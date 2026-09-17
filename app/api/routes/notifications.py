import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.realtime.broker import broker
from app.schemas.notification import (
    NotificationCreate,
    NotificationPage,
    NotificationRead,
    ReadAllResult,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def owned_notification(notification_id: int, user_id: int, db: Session) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Notification:
    if db.get(User, payload.recipient_id) is None:
        raise HTTPException(status_code=404, detail="Recipient not found")
    notification = Notification(**payload.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    event = NotificationRead.model_validate(notification).model_dump(mode="json")
    await broker.publish(notification.recipient_id, {"event": "notification.created", "notification": event})
    return notification


@router.get("", response_model=NotificationPage)
def list_notifications(
    unread_only: bool = False,
    notification_type: NotificationType | None = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationPage:
    filters = [Notification.recipient_id == current_user.id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))
    if notification_type:
        filters.append(Notification.type == notification_type)

    total = db.scalar(select(func.count()).select_from(Notification).where(*filters)) or 0
    unread = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.recipient_id == current_user.id,
            Notification.is_read.is_(False),
        )
    ) or 0
    items = list(
        db.scalars(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return NotificationPage(
        items=items,
        total=total,
        unread=unread,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.patch("/read-all", response_model=ReadAllResult)
def mark_all_as_read(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ReadAllResult:
    result = db.execute(
        update(Notification)
        .where(Notification.recipient_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    db.commit()
    return ReadAllResult(updated=result.rowcount or 0)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Notification:
    notification = owned_notification(notification_id, current_user.id, db)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    notification = owned_notification(notification_id, current_user.id, db)
    db.delete(notification)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
