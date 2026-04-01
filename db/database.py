from __future__ import annotations

import json
import logging
import os
from datetime import datetime

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    origin      TEXT NOT NULL DEFAULT 'MAD',
    alerts      INTEGER NOT NULL DEFAULT 0,
    budget      REAL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scan_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    scanned_at  TEXT NOT NULL DEFAULT (datetime('now')),
    cheapest    REAL,
    results     TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


async def _get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    db = await _get_db()
    try:
        await db.executescript(_SCHEMA)
        await db.commit()
    finally:
        await db.close()
    logger.info("Database initialised at %s", DB_PATH)


async def upsert_user(
    user_id: int,
    username: str | None = None,
    origin: str | None = None,
    alerts: bool | None = None,
    budget: float | None = None,
) -> None:
    db = await _get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        now = datetime.utcnow().isoformat()
        if row:
            parts, params = [], []
            if origin is not None:
                parts.append("origin = ?")
                params.append(origin)
            if alerts is not None:
                parts.append("alerts = ?")
                params.append(int(alerts))
            if budget is not None:
                parts.append("budget = ?")
                params.append(budget)
            if username is not None:
                parts.append("username = ?")
                params.append(username)
            if parts:
                parts.append("updated_at = ?")
                params.append(now)
                params.append(user_id)
                await db.execute(
                    f"UPDATE users SET {', '.join(parts)} WHERE user_id = ?",
                    params,
                )
        else:
            await db.execute(
                "INSERT INTO users (user_id, username, origin, alerts, budget, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    username or "",
                    origin or "MAD",
                    int(alerts) if alerts is not None else 0,
                    budget,
                    now,
                    now,
                ),
            )
        await db.commit()
    finally:
        await db.close()


async def get_user(user_id: int) -> dict | None:
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        if rows:
            return dict(rows[0])
        return None
    finally:
        await db.close()


async def get_alert_users() -> list[dict]:
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM users WHERE alerts = 1"
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def save_scan_result(
    user_id: int, cheapest: float, results_json: str
) -> None:
    db = await _get_db()
    try:
        await db.execute(
            "INSERT INTO scan_results (user_id, cheapest, results) VALUES (?, ?, ?)",
            (user_id, cheapest, results_json),
        )
        await db.commit()
    finally:
        await db.close()


async def get_last_cheapest(user_id: int) -> float | None:
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT cheapest FROM scan_results WHERE user_id = ? ORDER BY scanned_at DESC LIMIT 1",
            (user_id,),
        )
        if rows:
            return rows[0]["cheapest"]
        return None
    finally:
        await db.close()
