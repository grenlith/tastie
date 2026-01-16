from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import hash_password, verify_password
from core.result import Result
from models.models import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, username: str, email: str, password: str) -> Result[User]:
        errors: list[str] = []

        username = username.lower().strip()
        if len(username) < 3 or len(username) > 30:
            errors.append("username must be 3-30 characters")

        if not errors:
            existing = await self.db.execute(
                select(User).where(or_(User.username == username, User.email == email.lower()))
            )
            if existing.scalar_one_or_none():
                errors.append("error handling request")

        if errors:
            return Result.failure(*errors)

        user = User(
            username=username,
            email=email.lower(),
            password_hash=hash_password(password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return Result.success(user)

    async def authenticate_user(self, username: str, password: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                or_(User.username == username.lower(), User.email == username.lower())
            )
        )
        user = result.scalar_one_or_none()

        if user and verify_password(password, user.password_hash):
            return user
        return None

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username.lower()))
        return result.scalar_one_or_none()
