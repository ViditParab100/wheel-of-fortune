import hmac
import os
import random
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

import storage
import torn_api

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

UPLOAD_DIR = os.path.join(app.static_folder, "uploads")

storage.ensure_data_files()
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------------- helpers --

def window_is_open(state):
    if state.get("manually_closed"):
        return False
    start, end = state.get("window_start"), state.get("window_end")
    if not start or not end:
        return False
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return False
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return start_dt <= now <= end_dt


def public_segment(seg):
    return {"id": seg["id"], "label": seg["label"], "color": seg.get("color", "#999999"), "image": seg.get("image")}


def require_admin():
    return session.get("is_admin") is True


# -------------------------------------------------------------- player UI --

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    state = storage.load_state()
    return jsonify(
        {
            "open": window_is_open(state),
            "window_start": state.get("window_start"),
            "window_end": state.get("window_end"),
        }
    )


@app.route("/api/segments")
def api_segments():
    segments = storage.load_segments()
    return jsonify([public_segment(s) for s in segments])


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json(silent=True) or {}
    result = torn_api.verify_key(data.get("api_key", ""))
    # The API key itself stops existing here - never written to session,
    # disk, or logs. Only the derived name + id continue on.
    if not result["ok"]:
        return jsonify({"ok": False, "error": result["error"]}), 400

    state = storage.load_state()
    if not window_is_open(state):
        return jsonify({"ok": False, "error": "The spin window is currently closed."}), 403

    window_id = state["window_id"]
    if storage.has_spun(result["torn_id"], window_id):
        return jsonify({"ok": False, "error": "You've already used your spin for this window."}), 403

    session["torn_id"] = result["torn_id"]
    session["torn_name"] = result["torn_name"]
    session["verified_window_id"] = window_id

    return jsonify({"ok": True, "torn_name": result["torn_name"]})


@app.route("/api/spin", methods=["POST"])
def api_spin():
    state = storage.load_state()
    if not window_is_open(state):
        return jsonify({"ok": False, "error": "The spin window is currently closed."}), 403

    window_id = state["window_id"]
    torn_id = session.get("torn_id")
    torn_name = session.get("torn_name")
    if not torn_id or session.get("verified_window_id") != window_id:
        return jsonify({"ok": False, "error": "Please verify your Torn API key first."}), 401

    segments = storage.load_segments()
    if not segments:
        return jsonify({"ok": False, "error": "The wheel has no prizes configured yet."}), 500

    weights = [max(0, s.get("weight", 1)) for s in segments]
    chosen = random.choices(segments, weights=weights, k=1)[0]

    recorded = storage.check_and_record_spin(torn_id, torn_name, chosen["id"], chosen["prize"], window_id)
    if not recorded:
        return jsonify({"ok": False, "error": "You've already used your spin for this window."}), 403

    session.pop("torn_id", None)
    session.pop("torn_name", None)
    session.pop("verified_window_id", None)

    return jsonify({"ok": True, "segment_id": chosen["id"], "label": chosen["label"], "prize": chosen["prize"]})


# ------------------------------------------------------------------ admin --

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        submitted = request.form.get("password", "")
        if ADMIN_PASSWORD and hmac.compare_digest(submitted, ADMIN_PASSWORD):
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Incorrect password."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))
    state = storage.load_state()
    segments = storage.load_segments()
    spins = list(reversed(storage.get_all_spins()))
    return render_template(
        "admin.html",
        state=state,
        segments=segments,
        spins=spins,
        window_open=window_is_open(state),
        now_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


@app.route("/admin/window", methods=["POST"])
def admin_window():
    if not require_admin():
        return jsonify({"ok": False, "error": "Not authorized."}), 401

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    state = storage.load_state()

    if action == "open_new_window":
        state["window_id"] = state.get("window_id", 0) + 1
        state["manually_closed"] = False
        state["window_start"] = data.get("window_start") or datetime.now(timezone.utc).isoformat()
        state["window_end"] = data.get("window_end")
    elif action == "update_times":
        state["window_start"] = data.get("window_start")
        state["window_end"] = data.get("window_end")
    elif action == "close_now":
        state["manually_closed"] = True
    elif action == "reopen":
        state["manually_closed"] = False
    else:
        return jsonify({"ok": False, "error": "Unknown action."}), 400

    storage.save_state(state)
    return jsonify({"ok": True, "state": state, "open": window_is_open(state)})


@app.route("/admin/segments", methods=["POST"])
def admin_segments():
    if not require_admin():
        return jsonify({"ok": False, "error": "Not authorized."}), 401

    data = request.get_json(silent=True) or {}
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        return jsonify({"ok": False, "error": "At least one segment is required."}), 400

    cleaned = []
    for seg in segments:
        sid = (seg.get("id") or "").strip() or uuid.uuid4().hex[:8]
        try:
            weight = max(0, int(seg.get("weight", 1)))
        except (TypeError, ValueError):
            weight = 1
        cleaned.append(
            {
                "id": sid,
                "label": (seg.get("label") or "Prize").strip(),
                "prize": (seg.get("prize") or seg.get("label") or "Prize").strip(),
                "weight": weight,
                "color": seg.get("color") or "#999999",
                "image": seg.get("image"),
            }
        )

    storage.save_segments(cleaned)
    return jsonify({"ok": True, "segments": cleaned})


@app.route("/admin/segments/<segment_id>/image", methods=["POST"])
def admin_segment_image(segment_id):
    if not require_admin():
        return jsonify({"ok": False, "error": "Not authorized."}), 401

    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "No image uploaded."}), 400
    if not file.filename.lower().endswith(".png"):
        return jsonify({"ok": False, "error": "Only PNG images are supported."}), 400

    safe_id = secure_filename(segment_id) or uuid.uuid4().hex[:8]
    filename = f"{safe_id}.png"
    file.save(os.path.join(UPLOAD_DIR, filename))

    segments = storage.load_segments()
    for seg in segments:
        if seg["id"] == segment_id:
            seg["image"] = url_for("static", filename=f"uploads/{filename}") + f"?v={uuid.uuid4().hex[:6]}"
    storage.save_segments(segments)

    return jsonify({"ok": True, "segments": segments})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
