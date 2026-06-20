import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campaigns.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, column: str, ddl: str) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(campaigns)")}
    if column not in columns:
        conn.execute(f"ALTER TABLE campaigns ADD COLUMN {ddl}")


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                jd_text TEXT NOT NULL,
                top_k INTEGER NOT NULL,
                outreach_n INTEGER NOT NULL,
                result_json TEXT,
                selected_usernames TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "recipient_emails", "recipient_emails TEXT")
        _ensure_column(conn, "send_results", "send_results TEXT")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_campaign(jd_text: str, top_k: int, outreach_n: int) -> Dict[str, Any]:
    campaign_id = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO campaigns (
                id, status, jd_text, top_k, outreach_n,
                result_json, selected_usernames, recipient_emails,
                send_results, error, created_at, updated_at
            ) VALUES (?, 'running', ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (campaign_id, jd_text, top_k, outreach_n, now, now),
        )
    return get_campaign(campaign_id)


def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    result = dict(row)
    result["result"] = json.loads(result.pop("result_json") or "null")
    selected = result.pop("selected_usernames")
    result["selected_usernames"] = json.loads(selected) if selected else None
    emails = result.pop("recipient_emails", None)
    result["recipient_emails"] = json.loads(emails) if emails else None
    send_results = result.pop("send_results", None)
    result["send_results"] = json.loads(send_results) if send_results else None
    return result


def mark_ready(campaign_id: str, result: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE campaigns
            SET status = 'ready', result_json = ?, error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(result), _now(), campaign_id),
        )


def mark_failed(campaign_id: str, error: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE campaigns
            SET status = 'failed', error = ?, updated_at = ?
            WHERE id = ?
            """,
            (error, _now(), campaign_id),
        )


def save_selection(
    campaign_id: str,
    usernames: List[str],
    emails: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    campaign = get_campaign(campaign_id)
    if campaign is None:
        return None
    if campaign["status"] not in {"ready", "confirmed"}:
        raise ValueError(
            f"Campaign status is '{campaign['status']}', expected 'ready' or 'confirmed'"
        )

    with _connect() as conn:
        conn.execute(
            """
            UPDATE campaigns
            SET status = 'confirmed',
                selected_usernames = ?,
                recipient_emails = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(usernames),
                json.dumps(emails or {}),
                _now(),
                campaign_id,
            ),
        )
    return get_campaign(campaign_id)


def save_send_results(
    campaign_id: str, send_results: List[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    sent_count = sum(1 for item in send_results if item.get("status") == "sent")
    status = "sent" if sent_count else "confirmed"

    with _connect() as conn:
        conn.execute(
            """
            UPDATE campaigns
            SET status = ?, send_results = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, json.dumps(send_results), _now(), campaign_id),
        )
    return get_campaign(campaign_id)
