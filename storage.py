"""Flat-file storage: a CSV spin log plus small JSON config files.

No database service, no external dependency to pay for. Everything lives
under data/ on whatever disk the app runs on (must be a *persistent* disk,
e.g. PythonAnywhere's home directory - not an ephemeral container).
"""
import csv
import json
import os
import shutil
from datetime import datetime, timezone

from filelock import FileLock

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
SEGMENTS_PATH = os.path.join(DATA_DIR, "segments.json")
SEGMENTS_DEFAULT_PATH = os.path.join(DATA_DIR, "segments.default.json")
SPINS_CSV_PATH = os.path.join(DATA_DIR, "spins.csv")
LOCK_PATH = os.path.join(DATA_DIR, "storage.lock")

CSV_FIELDS = ["timestamp", "window_id", "torn_id", "torn_name", "segment_id", "prize"]

DEFAULT_STATE = {
    "window_id": 1,
    "window_start": None,
    "window_end": None,
    # Safe default: nobody can spin until an admin explicitly opens a window.
    "manually_closed": True,
}


def _lock():
    return FileLock(LOCK_PATH, timeout=10)


def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STATE_PATH):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STATE, f, indent=2)
    if not os.path.exists(SEGMENTS_PATH):
        shutil.copyfile(SEGMENTS_DEFAULT_PATH, SEGMENTS_PATH)
    if not os.path.exists(SPINS_CSV_PATH):
        with open(SPINS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def load_state():
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with _lock():
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)


def load_segments():
    with open(SEGMENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_segments(segments):
    with _lock():
        with open(SEGMENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=2)


def get_all_spins():
    with open(SPINS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def has_spun(torn_id, window_id):
    torn_id = str(torn_id)
    window_id = str(window_id)
    for row in get_all_spins():
        if row["torn_id"] == torn_id and row["window_id"] == window_id:
            return True
    return False


def check_and_record_spin(torn_id, torn_name, segment_id, prize, window_id):
    """Atomically check-then-append so two near-simultaneous requests from the
    same player can't both slip through and record two spins."""
    with _lock():
        for row in get_all_spins():
            if row["torn_id"] == str(torn_id) and row["window_id"] == str(window_id):
                return False
        with open(SPINS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "window_id": window_id,
                    "torn_id": torn_id,
                    "torn_name": torn_name,
                    "segment_id": segment_id,
                    "prize": prize,
                }
            )
        return True
