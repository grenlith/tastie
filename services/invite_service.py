import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.result import Result
from models.models import InviteCode

# unambiguous chars (excludes 0/O, 1/I/L)
INVITE_CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_PREFIX = "TASTIE-"
INVITE_CODE_LENGTH = 7


class InviteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_code() -> str:
        random_part = "".join(secrets.choice(INVITE_CODE_CHARS) for _ in range(INVITE_CODE_LENGTH))
        return f"{INVITE_CODE_PREFIX}{random_part}"

    async def create_invite_code(self) -> InviteCode:
        code = self.generate_code()
        invite = InviteCode(code=code)
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return invite

    async def get_code_by_value(self, code: str) -> InviteCode | None:
        result = await self.db.execute(
            select(InviteCode).where(InviteCode.code == code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def is_code_valid(self, code: str) -> bool:
        invite = await self.get_code_by_value(code)
        return invite is not None and invite.used_by_user_id is None

    async def validate_and_use_code(self, code: str, user_id: int) -> Result[InviteCode]:
        code = code.strip().upper()

        if not code.startswith(INVITE_CODE_PREFIX):
            return Result.failure("invalid invite code")

        if len(code) != len(INVITE_CODE_PREFIX) + INVITE_CODE_LENGTH:
            return Result.failure("invalid invite code")

        invite = await self.get_code_by_value(code)

        if not invite:
            return Result.failure("invalid invite code")

        if invite.used_by_user_id is not None:
            return Result.failure("invalid invite code")

        invite.used_by_user_id = user_id
        invite.used_at = datetime.now(UTC)
        await self.db.commit()

        return Result.success(invite)
