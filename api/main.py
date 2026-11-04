"""FastAPI leaderboard server with SQLite database."""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os

app = FastAPI(title="Leaderboard API")

DATABASE_PATH = "game.db"


def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_score REAL NOT NULL,
            runs_played INTEGER DEFAULT 0,
            best_score REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_name) REFERENCES players(name)
        )
    """)
    
    conn.commit()
    conn.close()


class ScoreSubmit(BaseModel):
    """Request model for submitting a score."""
    name: str
    score: float


class PlayerStats(BaseModel):
    """Response model for player stats."""
    name: str
    total_score: float
    runs_played: int
    best_score: float
    recent_scores: List[float]


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.post("/scores")
async def submit_score(score_data: ScoreSubmit):
    """Submit a new score for a player."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert or ignore player
        cursor.execute(
            "INSERT OR IGNORE INTO players (name, total_score, runs_played, best_score) VALUES (?, 0, 0, 0)",
            (score_data.name,)
        )
        
        # Insert score
        cursor.execute(
            "INSERT INTO scores (player_name, score) VALUES (?, ?)",
            (score_data.name, score_data.score)
        )
        
        # Update player stats
        cursor.execute(
            """
            UPDATE players 
            SET total_score = total_score + ?,
                runs_played = runs_played + 1,
                best_score = MAX(best_score, ?)
            WHERE name = ?
            """,
            (score_data.score, score_data.score, score_data.name)
        )
        
        conn.commit()
        return {"status": "success", "message": f"Score submitted for {score_data.name}"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/scores/top")
async def get_top_scores(limit: int = Query(10, ge=1, le=100)):
    """Get the top scores across all players."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.score, p.name
        FROM scores s
        JOIN players p ON s.player_name = p.name
        ORDER BY s.score DESC
        LIMIT ?
    """, (limit,))
    
    results = cursor.fetchall()
    conn.close()
    
    return {"top_scores": [{"name": row["name"], "score": row["score"]} for row in results]}


@app.get("/players/{name}/stats")
async def get_player_stats(name: str):
    """Get stats for a specific player."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if player exists
    cursor.execute("SELECT * FROM players WHERE name = ?", (name,))
    player = cursor.fetchone()
    
    if player is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Player '{name}' not found")
    
    # Get recent scores
    cursor.execute(
        "SELECT score FROM scores WHERE player_name = ? ORDER BY created_at DESC LIMIT 10",
        (name,)
    )
    recent_scores = [row["score"] for row in cursor.fetchall()]
    
    conn.close()
    
    return PlayerStats(
        name=player["name"],
        total_score=player["total_score"],
        runs_played=player["runs_played"],
        best_score=player["best_score"],
        recent_scores=recent_scores
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
