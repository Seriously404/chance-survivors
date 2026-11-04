"""Database operations for the leaderboard system."""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

DATABASE_PATH = "game.db"


def get_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_tables():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Players table
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
    
    # Scores table
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


def add_score(player_name: str, score: float) -> bool:
    """Add a score for a player."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert or ignore player
        cursor.execute(
            "INSERT OR IGNORE INTO players (name, total_score, runs_played, best_score) VALUES (?, 0, 0, 0)",
            (player_name,)
        )
        
        # Insert score
        cursor.execute(
            "INSERT INTO scores (player_name, score) VALUES (?, ?)",
            (player_name, score)
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
            (score, score, player_name)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_top_scores(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top scores."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.score, p.name
        FROM scores s
        JOIN players p ON s.player_name = p.name
        ORDER BY s.score DESC
        LIMIT ?
    """, (limit,))
    
    results = [{"name": row["name"], "score": row["score"]} for row in cursor.fetchall()]
    conn.close()
    
    return results


def get_player_stats(player_name: str) -> Optional[Dict[str, Any]]:
    """Get player stats."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if player exists
    cursor.execute("SELECT * FROM players WHERE name = ?", (player_name,))
    player = cursor.fetchone()
    
    if player is None:
        conn.close()
        return None
    
    # Get recent scores
    cursor.execute(
        "SELECT score FROM scores WHERE player_name = ? ORDER BY created_at DESC LIMIT 10",
        (player_name,)
    )
    recent_scores = [row["score"] for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "name": player["name"],
        "total_score": player["total_score"],
        "runs_played": player["runs_played"],
        "best_score": player["best_score"],
        "recent_scores": recent_scores
    }


def player_exists(player_name: str) -> bool:
    """Check if a player exists."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM players WHERE name = ?", (player_name,))
    result = cursor.fetchone() is not None
    
    conn.close()
    return result
