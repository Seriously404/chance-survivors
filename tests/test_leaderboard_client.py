"""Tests for explicit run upload payloads and HTTP validation."""

import json
import unittest
from unittest.mock import patch

from game.systems.leaderboard_client import build_run_submission, submit_run
from game.systems.numbers import LargeNumber


class LeaderboardClientTests(unittest.TestCase):
    def test_build_submission_preserves_large_score_and_build(self) -> None:
        inventory = [{
            "id": "rare-rifle",
            "name": "Rare Rifle",
            "type": "weapon",
            "level": 12,
            "stats": {"damage": 17},
            "combinations": [None],
        }]
        payload = build_run_submission(
            name="Player One",
            score=LargeNumber("1.797e308"),
            runtime_seconds=73.5,
            level=12,
            luck=4.5,
            inventory=inventory,
            active_slots={"weapons": ["rare-rifle"], "abilities": [None]},
            stats={"currency": {"Gold": LargeNumber("1e40")}},
        )

        self.assertEqual(payload["score"], "1.797E+308")
        self.assertEqual(payload["active_items"], ["rare-rifle"])
        self.assertEqual(payload["inventory"][0]["id"], "rare-rifle")
        self.assertEqual(payload["stats"]["currency"]["Gold"], "1E+40")
        json.dumps(payload, allow_nan=False)

    def test_submit_run_posts_to_leaderboard_endpoint(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, _size):
                return b'{"id": 9, "status": "accepted"}'

        payload = {"name": "A", "score": "1"}
        with patch("game.systems.leaderboard_client.urlopen", return_value=FakeResponse()) as open_url:
            result = submit_run(payload, base_url="http://leaderboard.test")

        self.assertEqual(result, {"id": 9, "status": "accepted"})
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "http://leaderboard.test/api/submit-run")
        self.assertEqual(json.loads(request.data), payload)

    def test_rejects_bad_leaderboard_url_and_response(self) -> None:
        with self.assertRaises(ValueError):
            submit_run({}, base_url="ftp://invalid.test")

        class InvalidResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, _size):
                return b'{"status": "rejected"}'

        with patch("game.systems.leaderboard_client.urlopen", return_value=InvalidResponse()):
            with self.assertRaises(ValueError):
                submit_run({}, base_url="http://leaderboard.test")


if __name__ == "__main__":
    unittest.main()
