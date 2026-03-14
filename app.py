from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory cache — scrapes GotsPort at most once per hour
# ---------------------------------------------------------------------------
_cache = {}
CACHE_TTL = timedelta(hours=1)


def get_data():
    now = datetime.now()
    if "data" in _cache and now - _cache["fetched_at"] < CACHE_TTL:
        return _cache["data"], _cache["fetched_at"]

    from scraper import get_league_data, get_tournament_data
    data = {
        "league":     get_league_data(),
        "tournament": get_tournament_data(),
    }
    _cache["data"]       = data
    _cache["fetched_at"] = now
    return data, now


@app.route("/")
def index():
    try:
        data, fetched_at = get_data()
        league     = data["league"]
        tournament = data["tournament"]
        last_updated = fetched_at.strftime("%b %d, %Y at %I:%M %p")
    except Exception as e:
        # Fall back gracefully — show error in header but keep page up
        league     = {"name": "NorCal Premier Spring 2025–26", "division": "", "coach": "", "standings": [], "schedule": []}
        tournament = {"name": "Players College Showcase 2026",  "location": "", "dates": "", "division": "", "brackets": [], "results": [], "upcoming": []}
        last_updated = f"Error fetching data: {e}"

    return render_template(
        "index.html",
        tournament=tournament,
        league=league,
        last_updated=last_updated,
    )


@app.route("/api/refresh")
def refresh():
    """Force a fresh scrape, bypassing the cache."""
    _cache.clear()
    try:
        data, fetched_at = get_data()
        return jsonify({"status": "ok", "refreshed_at": fetched_at.isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
