"""
Sudoku 2.O – Python Flask Backend
Run: pip install flask flask-cors
Then: python app.py
Serves the game at http://localhost:5000
"""

import os
import json
import random
import time
from datetime import datetime, date
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

# ---------------------------------------------------------------------------
# In-memory "database" (replace with SQLite / PostgreSQL for production)
# ---------------------------------------------------------------------------
_users = {}          # {session_id: {stats, levelStars, unlocked, lang, sfx, bgm}}
_daily_cache = {}    # {date_str: {seed: int}}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_session():
    sid = request.headers.get("X-Session-Id", "default")
    if sid not in _users:
        _users[sid] = {
            "stats": {
                "solved": 0,
                "streak": 0,
                "lastDate": "",
                "bestTime": 999999,
                "eStars": 0,
                "mStars": 0,
                "hStars": 0,
            },
            "levelStars": {"easy": {}, "medium": {}, "hard": {}},
            "unlocked":   {"easy": 1,  "medium": 1,  "hard": 1},
            "lang": "English",
            "sfxOn": True,
            "bgmOn": True,
            "dailyDone": "",
            "weeklyDone": 0,
        }
    return sid, _users[sid]


def sudoku_ok(board, r, c, v, n, br, bc):
    for x in range(n):
        if board[r][x] == v or board[x][c] == v:
            return False
    sr, sc = (r // br) * br, (c // bc) * bc
    for i in range(br):
        for j in range(bc):
            if board[sr + i][sc + j] == v:
                return False
    return True


def generate_solved(n, br, bc, seed=None):
    rng = random.Random(seed)
    b = [[0] * n for _ in range(n)]
    nums = list(range(1, n + 1))

    def solve(b):
        for r in range(n):
            for c in range(n):
                if not b[r][c]:
                    shuffled = nums[:]
                    rng.shuffle(shuffled)
                    for v in shuffled:
                        if sudoku_ok(b, r, c, v, n, br, bc):
                            b[r][c] = v
                            if solve(b):
                                return True
                            b[r][c] = 0
                    return False
        return True

    solve(b)
    return b


def make_puzzle(sol, n, remove_n, seed=None):
    rng = random.Random(seed)
    p = [row[:] for row in sol]
    cnt, att = 0, 0
    cells = [(r, c) for r in range(n) for c in range(n) if p[r][c]]
    rng.shuffle(cells)
    for r, c in cells:
        if cnt >= remove_n:
            break
        p[r][c] = 0
        cnt += 1
    return p


REMOVE_MAP = {
    "easy":   [6, 7, 8, 9, 10],
    "medium": [40, 44, 47, 50, 52, 54, 56],
    "hard":   [60, 65, 70, 74, 78, 82, 86, 90, 94, 98],
}
N_MAP   = {"easy": 4,  "medium": 9,  "hard": 12}
BR_MAP  = {"easy": 2,  "medium": 3,  "hard": 3}
BC_MAP  = {"easy": 2,  "medium": 3,  "hard": 4}
TIME_MAP = {"easy": 300, "medium": 900, "hard": 1500}


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


# ---------------------------------------------------------------------------
# API: Generate a puzzle
# ---------------------------------------------------------------------------
@app.route("/api/puzzle", methods=["POST"])
def api_puzzle():
    data = request.get_json(silent=True) or {}
    chapter = data.get("chapter", "easy")
    level = int(data.get("level", 1))
    seed = data.get("seed")  # optional; pass for reproducible puzzles

    n  = N_MAP.get(chapter, 4)
    br = BR_MAP.get(chapter, 2)
    bc = BC_MAP.get(chapter, 2)
    remove_map = REMOVE_MAP.get(chapter, [6])
    rm_idx = min(level - 1, len(remove_map) - 1)
    rm = remove_map[rm_idx]

    solved = generate_solved(n, br, bc, seed)
    puzzle = make_puzzle(solved, n, rm, seed)

    return jsonify({
        "n": n, "br": br, "bc": bc,
        "puzzle": puzzle,
        "solved": solved,
        "timeLimit": TIME_MAP.get(chapter, 300),
    })


# ---------------------------------------------------------------------------
# API: Save / load player stats
# ---------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def api_stats_get():
    sid, user = get_session()
    return jsonify(user)


@app.route("/api/stats", methods=["POST"])
def api_stats_post():
    sid, user = get_session()
    data = request.get_json(silent=True) or {}

    # Merge stats
    for key in ("stats", "levelStars", "unlocked"):
        if key in data:
            user[key] = data[key]
    for key in ("lang", "sfxOn", "bgmOn", "dailyDone", "weeklyDone"):
        if key in data:
            user[key] = data[key]

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API: Record a completed level
# ---------------------------------------------------------------------------
@app.route("/api/complete", methods=["POST"])
def api_complete():
    sid, user = get_session()
    data = request.get_json(silent=True) or {}
    chapter = data.get("chapter", "easy")
    level = int(data.get("level", 1))
    stars = int(data.get("stars", 1))
    elapsed = int(data.get("elapsed", 0))
    had_wrong = bool(data.get("hadWrong", False))
    challenge_mode = data.get("challengeMode")

    # Update level stars
    prev = user["levelStars"].get(chapter, {}).get(str(level), 0)
    if stars > prev:
        if chapter not in user["levelStars"]:
            user["levelStars"][chapter] = {}
        user["levelStars"][chapter][str(level)] = stars

    # Unlock next level
    max_lvs = {"easy": 5, "medium": 7, "hard": 10}
    if not challenge_mode and level < max_lvs.get(chapter, 5):
        user["unlocked"][chapter] = max(user["unlocked"].get(chapter, 1), level + 1)

    # Update stats
    s = user["stats"]
    s["solved"] = s.get("solved", 0) + 1
    today = date.today().strftime("%a %b %d %Y")
    if s.get("lastDate") != today:
        import datetime as dt
        yd = (dt.date.today() - dt.timedelta(days=1)).strftime("%a %b %d %Y")
        if s.get("lastDate") != yd:
            s["streak"] = 0
        s["streak"] = s.get("streak", 0) + 1
        s["lastDate"] = today
    if elapsed < s.get("bestTime", 999999):
        s["bestTime"] = elapsed
    if chapter == "easy":
        s["eStars"] = s.get("eStars", 0) + stars
    elif chapter == "medium":
        s["mStars"] = s.get("mStars", 0) + stars
    else:
        s["hStars"] = s.get("hStars", 0) + stars

    if challenge_mode == "daily":
        user["dailyDone"] = today
    if challenge_mode == "weekly":
        user["weeklyDone"] = int(time.time() // (7 * 86400))

    return jsonify({"ok": True, "stats": s, "unlocked": user["unlocked"], "levelStars": user["levelStars"]})


# ---------------------------------------------------------------------------
# API: Daily puzzle seed (same for everyone on the same date)
# ---------------------------------------------------------------------------
@app.route("/api/daily-seed", methods=["GET"])
def api_daily_seed():
    today = date.today().isoformat()
    if today not in _daily_cache:
        _daily_cache[today] = {"seed": random.randint(1, 999999)}
    return jsonify({"date": today, "seed": _daily_cache[today]["seed"]})


# ---------------------------------------------------------------------------
# API: Validate a full solved board (anti-cheat)
# ---------------------------------------------------------------------------
@app.route("/api/validate", methods=["POST"])
def api_validate():
    data = request.get_json(silent=True) or {}
    chapter = data.get("chapter", "easy")
    board = data.get("board", [])
    solved = data.get("solved", [])

    if not board or not solved:
        return jsonify({"valid": False, "error": "Missing board or solution"}), 400

    n = N_MAP.get(chapter, 4)
    if len(board) != n or any(len(row) != n for row in board):
        return jsonify({"valid": False, "error": "Board size mismatch"}), 400

    # Check board matches solution
    for r in range(n):
        for c in range(n):
            if board[r][c] != solved[r][c]:
                return jsonify({"valid": False})

    return jsonify({"valid": True})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🌸 Sudoku 2.O Backend running at http://localhost:{port}")
    print("   Serving game files from current directory.")
    print("   Press Ctrl+C to stop.\n")
    app.run(debug=True, host="0.0.0.0", port=port)