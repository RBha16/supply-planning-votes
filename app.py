import os
import json
import logging
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "votes.json")
_lock = threading.Lock()


def _load_all():
    if not os.path.exists(VOTES_FILE):
        return {}
    try:
        with open(VOTES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data):
    with open(VOTES_FILE, "w") as f:
        json.dump(data, f)


# --------------- Page routes ---------------

@app.route("/")
def voting_page():
    return render_template("voting.html")


@app.route("/results")
def results_page():
    return render_template("results.html")


@app.route("/reference")
def reference_page():
    return render_template("reference.html")


# --------------- API routes ----------------

@app.route("/api/vote", methods=["POST"])
def submit_vote():
    data = request.get_json(force=True)
    participant = data.get("participant", "").strip()
    votes_data = data.get("votes", {})

    if not participant:
        return jsonify({"error": "participant name is required"}), 400
    if not votes_data:
        return jsonify({"error": "votes payload is empty"}), 400

    now = datetime.now(timezone.utc).isoformat()

    with _lock:
        all_votes = _load_all()
        all_votes[participant] = {
            "participant": participant,
            "timestamp": now,
            "votes": votes_data,
        }
        _save_all(all_votes)

    app.logger.info("Vote saved for %s (%d items)", participant, len(votes_data))
    return jsonify({"status": "ok", "participant": participant})


@app.route("/api/votes", methods=["GET"])
def get_votes():
    with _lock:
        all_votes = _load_all()
    submissions = sorted(all_votes.values(), key=lambda s: s.get("timestamp", ""))
    return jsonify(submissions)


@app.route("/api/status", methods=["GET"])
def vote_status():
    with _lock:
        all_votes = _load_all()
    return jsonify({"submitted": len(all_votes)})


# --------------- Startup --------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.logger.info("Starting on port %d, votes file: %s", port, VOTES_FILE)
    app.run(host="0.0.0.0", port=port, debug=False)
