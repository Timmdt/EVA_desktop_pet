from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMAND_FILE = ROOT / "pet_command.json"

VALID = {"idle", "happy", "curious", "sad", "display"}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1].lower() not in VALID:
        print("Benutzung:")
        print("  python control_pet.py idle")
        print("  python control_pet.py happy 3")
        print("  python control_pet.py curious 5")
        print("  python control_pet.py sad")
        print("  python control_pet.py display 8")
        return 1

    state = sys.argv[1].lower()

    payload = {"state": state}

    if len(sys.argv) >= 3:
        payload["duration"] = float(sys.argv[2])

    COMMAND_FILE.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    print(f"EVA Pet -> {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
