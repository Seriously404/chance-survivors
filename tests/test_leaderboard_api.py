"""Headless validation for the leaderboard API."""

import importlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


def load_app_module():
    temp_dir = Path(tempfile.mkdtemp(prefix="leaderboard-test-"))
    db_path = temp_dir / "leaderboard.db"
    os.environ["CHANCE_SURVIVORS_LEADERBOARD_DB"] = str(db_path)
    os.environ["CHANCE_SURVIVORS_ADMIN_TOKEN"] = "test-admin-token"
    import game.leaderboard_api as leaderboard_api

    return importlib.reload(leaderboard_api), db_path


leaderboard_api, _ = load_app_module()
client = TestClient(leaderboard_api.app)


class LeaderboardApiTests(unittest.TestCase):
    def setUp(self) -> None:
        leaderboard_api.initialize_db()
        response = client.post(
            "/admin/clear-leaderboard",
            headers={"Authorization": "Bearer test-admin-token"},
        )
        self.assertEqual(response.status_code, 200)

    def test_submit_and_fetch_entry(self) -> None:
        response = client.post(
            "/api/submit-run",
            json={
                "name": "Alice",
                "score": "123456789012345678901234567890123456789",
                "runtime_seconds": 72.5,
                "level": 24,
                "luck": 42.1,
                "inventory": [{"id": "rifle", "name": "Rifle"}, {"id": "boots", "name": "Boots"}],
                "active_items": ["rifle", "boots"],
                "stats": {"damage": 88, "crit_chance": 0.12},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        entry_id = data["id"]

        leaderboard = client.get("/api/leaderboard").json()
        self.assertEqual(len(leaderboard), 1)
        self.assertEqual(leaderboard[0]["name"], "Alice")
        self.assertEqual(leaderboard[0]["score"],
                         "123456789012345678901234567890123456789")

        detail = client.get(f"/api/leaderboard/{entry_id}").json()
        self.assertEqual(detail["level"], 24)
        self.assertEqual(detail["active_items"], ["rifle", "boots"])
        self.assertEqual(detail["inventory"][0]["name"], "Rifle")

    def test_legacy_server_exposes_leaderboard_and_interactive_docs(self) -> None:
        from api.main import app as legacy_app

        legacy = TestClient(legacy_app)
        self.assertEqual(legacy.get("/").status_code, 200)
        self.assertEqual(legacy.get("/docs").status_code, 200)
        schema = legacy.get("/openapi.json").json()
        self.assertIn("/api/submit-run", schema["paths"])
        self.assertIn("/players/{name}/stats", schema["paths"])

    def test_admin_clear_requires_valid_token(self) -> None:
        response = client.post("/admin/clear-leaderboard",
                               headers={"Authorization": "Bearer wrong-token"})
        self.assertEqual(response.status_code, 403)

        client.post(
            "/api/submit-run",
            json={
                "name": "Bob",
                "score": "5",
                "runtime_seconds": 10,
                "level": 2,
                "luck": 3.0,
                "inventory": [],
                "active_items": [],
                "stats": {},
            },
        )

        response = client.post(
            "/admin/clear-leaderboard",
            headers={"Authorization": "Bearer test-admin-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get("/api/leaderboard").json(), [])


if __name__ == "__main__":
    unittest.main()
