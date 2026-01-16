from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_VALID_FTS_TABLES = frozenset({"bookmarks_fts"})


def escape_fts5_query(query: str) -> str:
    """wrap each word in quotes for literal FTS5 matching."""
    words = query.replace('"', "").split()
    escaped_words = [f'"{word}"' for word in words if word]
    return " ".join(escaped_words)


async def fts5_search_ids(
    db: AsyncSession,
    table_name: str,
    query: str,
) -> Sequence[int]:
    """return matching row IDs ordered by FTS5 rank."""
    if table_name not in _VALID_FTS_TABLES:
        raise ValueError(f"Invalid FTS table: {table_name}")

    escaped_query = escape_fts5_query(query)
    if not escaped_query:
        return []

    fts_query = text(f"""
        SELECT rowid FROM {table_name}
        WHERE {table_name} MATCH :query
        ORDER BY rank
    """)
    result = await db.execute(fts_query, {"query": escaped_query})
    return [row[0] for row in result]
