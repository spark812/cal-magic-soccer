from flask import Flask, render_template, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Hardcoded seed data (from last scrape — refresh via /api/refresh)
# ---------------------------------------------------------------------------

TOURNAMENT_DATA = {
    "name": "Players College Showcase 2026",
    "location": "Las Vegas, NV",
    "dates": "March 13–15, 2026",
    "division": "Female U14 — Red Rock Division",
    "brackets": [
        {
            "name": "Bracket A",
            "standings": [
                {"team": "Arizona Soccer Club 2012G DPL",    "mp": 3, "w": 2, "l": 1, "d": 0, "gf": 4, "ga": 2, "gd": "+2", "pts": 6},
                {"team": "Las Vegas Storm FC G12 Academy",   "mp": 3, "w": 2, "l": 1, "d": 0, "gf": 7, "ga": 5, "gd": "+2", "pts": 6},
                {"team": "ALBION SC Central Valley G12 DPLO","mp": 3, "w": 1, "l": 1, "d": 1, "gf": 1, "ga": 3, "gd": "-2", "pts": 4},
                {"team": "LA Bulls G12 DPLO",                "mp": 3, "w": 0, "l": 2, "d": 1, "gf": 2, "ga": 4, "gd": "-2", "pts": 1},
            ],
        },
        {
            "name": "Bracket B",
            "standings": [
                {"team": "Cal Magic 2012G West",          "mp": 3, "w": 3, "l": 0, "d": 0, "gf": 6, "ga": 0, "gd": "+6", "pts": 9, "highlight": True},
                {"team": "Apple Valley SC G12 BLACK",     "mp": 3, "w": 2, "l": 1, "d": 0, "gf": 4, "ga": 2, "gd": "+2", "pts": 6},
                {"team": "Phoenix Rush Girls NL Premier 2","mp": 3, "w": 1, "l": 2, "d": 0, "gf": 1, "ga": 5, "gd": "-4", "pts": 3},
                {"team": "ALBION SC Idaho G12 Elite",     "mp": 3, "w": 0, "l": 3, "d": 0, "gf": 1, "ga": 5, "gd": "-4", "pts": 0},
            ],
        },
    ],
    "results": [
        {"date": "Mar 13", "home": "Phoenix Rush",   "away": "Cal Magic",      "score": "0–3", "result": "W"},
        {"date": "Mar 13", "home": "Cal Magic",      "away": "ALBION Idaho",   "score": "2–0", "result": "W"},
        {"date": "Mar 14", "home": "Cal Magic",      "away": "Apple Valley",   "score": "1–0", "result": "W"},
    ],
    "upcoming": [
        {"date": "Mar 14", "round": "Semifinal",    "home": "Cal Magic", "away": "Las Vegas Storm", "location": "Heritage Park #13"},
        {"date": "Mar 15", "round": "Championship", "home": "SF Winner", "away": "SF Winner",       "location": "Bettye Wilson #1 — 12:20 PM"},
    ],
}

LEAGUE_DATA = {
    "name": "NorCal Premier Spring 2025–26",
    "division": "Female U14 — Gold — Region 3/4 — Bracket A",
    "coach": "Alfredo Rocha",
    "standings": [
        {"team": "Revolution FC 12G Yellow",       "mp": 2, "w": 1, "l": 0, "d": 1, "gf": 1, "ga": 0,  "gd": "+1", "pts": 4},
        {"team": "Cal Magic 2012G West",            "mp": 1, "w": 1, "l": 0, "d": 0, "gf": 6, "ga": 2,  "gd": "+4", "pts": 3, "highlight": True},
        {"team": "Association FC 2012G Blue",       "mp": 1, "w": 0, "l": 0, "d": 1, "gf": 3, "ga": 3,  "gd": "0",  "pts": 1},
        {"team": "Solano Surf 12G White",           "mp": 1, "w": 0, "l": 0, "d": 1, "gf": 0, "ga": 0,  "gd": "0",  "pts": 1},
        {"team": "Livermore Fusion SC 2012 Gold",   "mp": 2, "w": 0, "l": 1, "d": 1, "gf": 3, "ga": 4,  "gd": "-1", "pts": 1},
        {"team": "1974 NFC 2012G Orange",           "mp": 0, "w": 0, "l": 0, "d": 0, "gf": 0, "ga": 0,  "gd": "0",  "pts": 0},
        {"team": "UC Premier 2012G Red",            "mp": 0, "w": 0, "l": 0, "d": 0, "gf": 0, "ga": 0,  "gd": "0",  "pts": 0},
        {"team": "Mt. Diablo Mustang 2012G White",  "mp": 1, "w": 0, "l": 1, "d": 0, "gf": 2, "ga": 6,  "gd": "-4", "pts": 0},
    ],
    "schedule": [
        {"date": "Mar 7, 2026",  "opponent": "Mt. Diablo Mustang 2012G White",        "time": "3:50 PM",  "location": "El Dorado Middle School",  "result": "W 6–2",  "status": "final"},
        {"date": "Mar 14, 2026", "opponent": "UC Premier 2012G Red",                  "time": "TBD",      "location": "TBD",                      "result": "",       "status": "upcoming"},
        {"date": "Mar 28, 2026", "opponent": "Revolution FC 12G Yellow",              "time": "5:10 PM",  "location": "Wilder Fields — Wilder #1", "result": "",       "status": "upcoming"},
        {"date": "Apr 11, 2026", "opponent": "1974 NFC 2012G Orange",                 "time": "11:40 AM", "location": "Wilder Fields — Wilder #1", "result": "",       "status": "upcoming"},
        {"date": "Apr 12, 2026", "opponent": "UC Premier 2012G Red",                  "time": "12:30 PM", "location": "Accinelli Park",            "result": "",       "status": "upcoming"},
        {"date": "Apr 18, 2026", "opponent": "Solano Surf 12G White",                 "time": "3:20 PM",  "location": "Wilder Fields — Wilder #1", "result": "",       "status": "upcoming"},
        {"date": "Apr 25, 2026", "opponent": "Livermore Fusion SC 2012 Gold",         "time": "9:50 AM",  "location": "Wilder Fields — Wilder #1", "result": "",       "status": "upcoming"},
        {"date": "Apr 26, 2026", "opponent": "Association Football Club 2012G Blue",  "time": "9:00 AM",  "location": "Witter Fields (PHS)",       "result": "",       "status": "upcoming"},
        {"date": "May 2, 2026",  "opponent": "Mt. Diablo Mustang 2012G White",        "time": "9:50 AM",  "location": "Wilder Fields — Wilder #1", "result": "",       "status": "upcoming"},
    ],
}


@app.route("/")
def index():
    return render_template(
        "index.html",
        tournament=TOURNAMENT_DATA,
        league=LEAGUE_DATA,
        last_updated=datetime.now().strftime("%b %d, %Y at %I:%M %p"),
    )


@app.route("/api/refresh")
def refresh():
    """Attempt a live scrape and return updated data as JSON."""
    try:
        from scraper import get_tournament_data, get_league_data
        return jsonify({
            "tournament": get_tournament_data(),
            "league": get_league_data(),
            "refreshed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
