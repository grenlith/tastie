from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, MetaData, Text, UniqueConstraint, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from collections.abc import Sequence


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_tags(tags: str) -> list[str]:
    return tags.split() if tags else []


class Visibility:
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    PRIVATE = "private"

    ALL = [PUBLIC, AUTHENTICATED, PRIVATE]


class Base(DeclarativeBase):
    pass  # this annoys me but is how sqlalchemy does things
    # https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True, index=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    bookmarks: Mapped[Sequence[Bookmark]] = relationship(
        "Bookmark", back_populates="user", cascade="all, delete-orphan"
    )
    invite_code_used: Mapped[InviteCode | None] = relationship(
        "InviteCode", back_populates="used_by", uselist=False
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_user_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str] = mapped_column(Text, index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(Text, default=Visibility.PUBLIC)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship("User", back_populates="bookmarks")

    normalized_tags: Mapped[Sequence[Tag]] = relationship(
        "Tag",
        secondary="bookmark_tags",
        back_populates="bookmarks",
        viewonly=True,
    )

    def tag_list(self) -> list[str]:
        return parse_tags(self.tags)

    @property
    def is_private(self) -> bool:
        return self.visibility == Visibility.PRIVATE

    @property
    def is_authenticated_only(self) -> bool:
        return self.visibility == Visibility.AUTHENTICATED


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, index=True)
    used_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    used_by: Mapped[User | None] = relationship("User", back_populates="invite_code_used")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    bookmarks: Mapped[Sequence[Bookmark]] = relationship(
        "Bookmark",
        secondary="bookmark_tags",
        back_populates="normalized_tags",
        viewonly=True,
    )


class BookmarkTag(Base):
    __tablename__ = "bookmark_tags"

    bookmark_id: Mapped[int] = mapped_column(
        ForeignKey("bookmarks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


FTS_SETUP_STATEMENTS = [
    """CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts USING fts5(
        title,
        description,
        tags,
        content='bookmarks',
        content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS bookmarks_ai AFTER INSERT ON bookmarks BEGIN
        INSERT INTO bookmarks_fts(rowid, title, description, tags)
        VALUES (new.id, new.title, new.description, new.tags);
    END""",
    """CREATE TRIGGER IF NOT EXISTS bookmarks_ad AFTER DELETE ON bookmarks BEGIN
        INSERT INTO bookmarks_fts(bookmarks_fts, rowid, title, description, tags)
        VALUES ('delete', old.id, old.title, old.description, old.tags);
    END""",
    """CREATE TRIGGER IF NOT EXISTS bookmarks_au AFTER UPDATE ON bookmarks BEGIN
        INSERT INTO bookmarks_fts(bookmarks_fts, rowid, title, description, tags)
        VALUES ('delete', old.id, old.title, old.description, old.tags);
        INSERT INTO bookmarks_fts(rowid, title, description, tags)
        VALUES (new.id, new.title, new.description, new.tags);
    END""",
]


@event.listens_for(Base.metadata, "after_create")
def create_fts_table(target: MetaData, connection: Connection, **kwargs: Any) -> None:
    for statement in FTS_SETUP_STATEMENTS:
        connection.execute(text(statement))
