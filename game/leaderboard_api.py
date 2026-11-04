"""Persistent FastAPI leaderboard for Chance Survivors.

The application stores run summaries in SQLite so the game can upload final runs
and an external website can render a leaderboard without exposing direct database
access.
"""

from __future__ import annotations

import json
import os
import sqlite3
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "leaderboard.db"
DB_PATH = Path(os.environ.get("CHANCE_SURVIVORS_LEADERBOARD_DB", DEFAULT_DB_PATH))
ADMIN_TOKEN_ENV = "CHANCE_SURVIVORS_ADMIN_TOKEN"


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    return value


def _as_decimal(raw: Any, field_name: str) -> Decimal:
    if isinstance(raw, Decimal):
        value = raw
    else:
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a valid numeric value") from exc
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return value


class RunSubmission(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1, max_length=32)
    score: Any
    runtime_seconds: float = Field(gt=0)
    level: int = Field(ge=1)
    luck: float = Field(ge=0)
    inventory: list[Any] = Field(default_factory=list)
    active_items: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned[:32]

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: Any) -> Any:
        _as_decimal(value, "score")
        return value

    @field_validator("inventory", "active_items", "stats")
    @classmethod
    def normalize_json(cls, value: Any) -> Any:
        if value is None:
            return [] if isinstance(value, list) else {}
        return value


app = FastAPI(title="Chance Survivors Leaderboard")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                score TEXT NOT NULL,
                runtime_seconds REAL NOT NULL,
                level INTEGER NOT NULL,
                luck REAL NOT NULL,
                inventory_json TEXT NOT NULL,
                active_items_json TEXT NOT NULL,
                stats_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_leaderboard_score ON leaderboard(score DESC)"
        )


initialize_db()


def _serialize_entry(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "score": row["score"],
        "runtime_seconds": float(row["runtime_seconds"]),
        "level": row["level"],
        "luck": float(row["luck"]),
        "inventory": json.loads(row["inventory_json"] or "[]"),
        "active_items": json.loads(row["active_items_json"] or "[]"),
        "stats": json.loads(row["stats_json"] or "{}"),
        "created_at": row["created_at"],
    }


def _admin_token() -> str:
    token = os.environ.get(ADMIN_TOKEN_ENV, "")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Set CHANCE_SURVIVORS_ADMIN_TOKEN before using administrative endpoints.",
        )
    return token


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    table_rows = ""
    rows = _list_entries(limit=25)
    for entry in rows:
        row = (
            "<tr class='entry-row' data-id='{id}' tabindex='0'>"
            "<td>{place}</td><td>{name}</td><td>{score}</td><td>{time}</td>"
            "</tr>"
        ).format(
            id=entry["id"],
            place=entry["place"],
            name=escape(entry["name"]),
            score=escape(entry["score"]),
            time=escape(f'{entry["runtime_seconds"]:.2f}s'),
        )
        table_rows += row
    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Chance Survivors Leaderboard</title>
      <style>
        :root {{ --bg: #08130d; --panel: #102719; --line: #1d4330; --text: #dfffe9; --muted: #9ec4aa; --green: #56e17c; --green-soft: #213d2b; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 24px; }}
        .wrap {{ max-width: 1080px; margin: 0 auto; }}
        h1 {{ color: var(--green); margin-bottom: 8px; }}
        .toolbar {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }}
        button {{ background: var(--green); color: #102719; border: none; border-radius: 8px; padding: 10px 14px; font-weight: bold; cursor: pointer; }}
        table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
        th, td {{ padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; }}
        th {{ color: var(--green); }}
        tbody tr:hover {{ background: var(--green-soft); }}
        .detail {{ margin-top: 24px; background: var(--panel); border: 1px solid var(--line); padding: 18px; display: none; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 12px; }}
        .chip {{ display: inline-block; background: var(--green-soft); border: 1px solid var(--line); border-radius: 999px; padding: 5px 9px; margin: 3px; color: var(--text); }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="toolbar">
          <h1>Chance Survivors Leaderboard</h1>
          <button id="clear-button" type="button">Clear leaderboard</button>
        </div>
        <table>
          <thead>
            <tr><th>Place</th><th>Name</th><th>Score</th><th>Time</th></tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
        <div id="detail" class="detail"></div>
      </div>
      <script>
        const table = document.querySelector('tbody');
        const detail = document.getElementById('detail');
        table.addEventListener('click', async (event) => {{
          const row = event.target.closest('.entry-row');
          if (!row) return;
          const id = row.dataset.id;
          const response = await fetch(`/api/leaderboard/${{id}}`);
          const entry = await response.json();
          detail.style.display = 'block';
          detail.innerHTML = `
            <h2>${{entry.name}}</h2>
            <div class="stats">
              <div><strong>Score:</strong> ${{entry.score}}</div>
              <div><strong>Time:</strong> ${{entry.runtime_seconds.toFixed(2)}}s</div>
              <div><strong>Level:</strong> ${{entry.level}}</div>
              <div><strong>Luck:</strong> ${{entry.luck}}</div>
            </div>
            <h3>Inventory</h3>
            <div>${{entry.inventory.map(item => `<span class="chip">${{item.name || item.id || JSON.stringify(item)}}</span>`).join('')}}</div>
            <h3>Active items</h3>
            <div>${{entry.active_items.map(item => `<span class="chip">${{item}}</span>`).join('')}}</div>
            <h3>Stats</h3>
            <pre>${{JSON.stringify(entry.stats, null, 2)}}</pre>
          `;
        }});

        document.getElementById('clear-button').addEventListener('click', async () => {{
          const token = prompt('Enter admin token');
          if (!token) return;
          const response = await fetch('/admin/clear-leaderboard', {{
            method: 'POST',
            headers: {{ 'Authorization': `Bearer ${{token}}`, 'Content-Type': 'application/json' }},
            body: JSON.stringify({{}})
          }});
          if (response.ok) {{
            window.location.reload();
          }} else {{
            alert('Clear failed: ' + (await response.text()));
          }}
        }});
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/leaderboard")
def leaderboard(limit: int = Query(25, ge=1, le=100)) -> list[dict[str, Any]]:
    return _list_entries(limit=limit)


@app.get("/api/leaderboard/{entry_id}")
def leaderboard_entry(entry_id: int) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM leaderboard WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _serialize_entry(row)


@app.post("/api/submit-run")
def submit_run(submission: RunSubmission) -> dict[str, Any]:
    score = _as_decimal(submission.score, "score")
    payload = {
        "name": submission.name,
        "score": str(score),
        "runtime_seconds": float(submission.runtime_seconds),
        "level": int(submission.level),
        "luck": float(submission.luck),
        "inventory": json.dumps(_json_ready(submission.inventory), separators=(",", ":")),
        "active_items": json.dumps(_json_ready(submission.active_items), separators=(",", ":")),
        "stats": json.dumps(_json_ready(submission.stats), separators=(",", ":")),
    }
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO leaderboard (name, score, runtime_seconds, level, luck, inventory_json, active_items_json, stats_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["score"],
                payload["runtime_seconds"],
                payload["level"],
                payload["luck"],
                payload["inventory"],
                payload["active_items"],
                payload["stats"],
            ),
        )
        row_id = cursor.lastrowid
    return {"id": row_id, "status": "accepted"}


@app.post("/admin/clear-leaderboard")
def clear_leaderboard(authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, str]:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.split(" ", 1)[1].strip()
    if token != _admin_token():
        raise HTTPException(status_code=403, detail="Invalid admin token")
    with _connect() as connection:
        connection.execute("DELETE FROM leaderboard")
    return {"status": "cleared"}


def _list_entries(limit: int = 25) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM leaderboard",
        ).fetchall()
    sorted_rows = sorted(rows, key=lambda row: Decimal(row["score"]), reverse=True)[:limit]
    results: list[dict[str, Any]] = []
    for index, row in enumerate(sorted_rows, start=1):
        entry = _serialize_entry(row)
        entry["place"] = index
        results.append(entry)
    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
