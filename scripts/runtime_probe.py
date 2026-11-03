"""Convenience launcher for the game's JSON runtime probe."""

import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from game.systems.runtime_probe import main


if __name__ == "__main__":
    main()
