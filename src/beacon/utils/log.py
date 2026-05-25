import asyncio
import aiosqlite
import os
from typing import Optional, Dict
from contextlib import asynccontextmanager


class LoggingManager:
    """Manages persisted guild log-channel mappings with a pooled SQLite backend.

    """
    def __init__(self, db_path: str):
        """Initialize logging storage paths, cache, and lazy pool state.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.log_channel_cache: Dict[int, int] = {}
        self.db_pool: Optional[asyncio.Queue] = None

    async def init_pools(self, pool_size: int = 5):
        """Create and warm a pool of SQLite connections for async reuse.

        Args:
            pool_size: Number of SQLite connections to keep in the pool.

        Returns:
            Any: Result produced by this function.
        """
        if self.db_pool is None:
            self.db_pool = asyncio.Queue(maxsize=pool_size)
            for _ in range(pool_size):
                conn = await aiosqlite.connect(
                    self.db_path,
                    timeout=5,
                )
                await conn.execute("PRAGMA busy_timeout=5000")
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous = NORMAL")
                await conn.commit()
                await self.db_pool.put(conn)

    async def close_pools(self):
        """Close all pooled database connections and reset pool state.

        Returns:
            Any: Result produced by this function.
        """
        if self.db_pool is not None:
            while not self.db_pool.empty():
                conn = await self.db_pool.get()
                await conn.close()
            self.db_pool = None

    @asynccontextmanager
    async def acquire_db(self):
        """Yield a pooled SQLite connection and return it when finished.

        Yields:
            Any: Items yielded during iteration.
        """
        if self.db_pool is None:
            await self.init_pools()
        conn = await self.db_pool.get()
        try:
            yield conn
        finally:
            await self.db_pool.put(conn)

    async def init_db(self):
        """Ensure required logging tables exist in the database.

        Returns:
            Any: Result produced by this function.
        """
        async def run_init():
            """Execute table-creation statements within a managed connection.

            Returns:
                Any: Result produced by this function.
            """
            async with self.acquire_db() as db:
                await db.execute('''
                                 CREATE TABLE IF NOT EXISTS log_channels
                                 (
                                     guild_id INTEGER PRIMARY KEY,
                                     channel_id INTEGER
                                 )
                                 ''')
                await db.commit()

        await run_init()

    async def populate_cache(self):
        """Refresh the in-memory guild-to-channel cache from database rows.

        Returns:
            Any: Result produced by this function.
        """
        self.log_channel_cache.clear()
        async with self.acquire_db() as db:
            async with db.execute("SELECT guild_id, channel_id FROM log_channels") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    self.log_channel_cache[row[0]] = row[1]

    async def get(self, guild_id: int) -> Optional[int]:
        """Return the configured log channel for a guild when available.

        Args:
            guild_id: Discord guild ID.

        Returns:
            Any: Result produced by this function.
        """
        if guild_id in self.log_channel_cache:
            return self.log_channel_cache[guild_id]

        async with self.acquire_db() as db:
            async with db.execute("SELECT channel_id FROM log_channels WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    self.log_channel_cache[guild_id] = row[0]
                    return row[0]
        return None

    async def set(self, guild_id: int, channel_id: int):
        """Persist and cache a guild's configured log channel.

        Args:
            guild_id: Discord guild ID.
            channel_id: Discord channel ID.

        Returns:
            Any: Result produced by this function.
        """
        async with self.acquire_db() as db:
            await db.execute(
                "INSERT OR REPLACE INTO log_channels (guild_id, channel_id) VALUES (?, ?)",
                (guild_id, channel_id)
            )
            await db.commit()
        self.log_channel_cache[guild_id] = channel_id

    async def remove(self, guild_id: int):
        """Delete a guild's log-channel mapping from storage and cache.

        Args:
            guild_id: Discord guild ID.

        Returns:
            Any: Result produced by this function.
        """
        async with self.acquire_db() as db:
            await db.execute("DELETE FROM log_channels WHERE guild_id = ?", (guild_id,))
            await db.commit()
        self.log_channel_cache.pop(guild_id, None)