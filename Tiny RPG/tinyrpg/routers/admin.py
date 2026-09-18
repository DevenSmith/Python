from fastapi import APIRouter
from sqlalchemy import select

from tinyrpg.database_models import UserRecord
from tinyrpg.dependencies import AdminUser, DatabaseSession
from tinyrpg.schemas.users import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users_for_admin(
    session: DatabaseSession, _admin: AdminUser
) -> list[UserResponse]:
    return [
        UserResponse.from_record(user)
        for user in session.scalars(select(UserRecord).order_by(UserRecord.id))
    ]
