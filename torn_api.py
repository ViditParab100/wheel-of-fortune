"""Talks to Torn's official API to resolve a player's public API key into
their Torn name + ID. The key itself is never stored or logged - it is used
for this one request and then discarded by the caller."""
import requests

TORN_API_URL = "https://api.torn.com/user/"


def verify_key(api_key):
    """Returns {"ok": True, "torn_id": int, "torn_name": str} or
    {"ok": False, "error": str}. Never raises - all failure modes are
    reported through the "ok" flag so callers can't accidentally log a key
    inside a traceback."""
    api_key = (api_key or "").strip()
    if not api_key:
        return {"ok": False, "error": "Please enter your Torn API key."}

    try:
        resp = requests.get(
            TORN_API_URL,
            params={"selections": "basic", "key": api_key},
            timeout=6,
        )
    except requests.RequestException:
        return {"ok": False, "error": "Could not reach the Torn API. Try again in a moment."}

    if resp.status_code != 200:
        return {"ok": False, "error": "Torn API returned an unexpected response."}

    try:
        payload = resp.json()
    except ValueError:
        return {"ok": False, "error": "Torn API returned an unexpected response."}

    if "error" in payload:
        message = payload["error"].get("error", "Invalid API key.")
        return {"ok": False, "error": f"Torn API rejected the key: {message}"}

    if "player_id" not in payload or "name" not in payload:
        return {"ok": False, "error": "Torn API response was missing player info."}

    return {"ok": True, "torn_id": payload["player_id"], "torn_name": payload["name"]}
