import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

TOURNAMENT_URL = "https://system.gotsport.com/org_event/events/44771/schedules?group=478899"
LEAGUE_URL     = "https://system.gotsport.com/org_event/events/49370/schedules?team=3796059"
CAL_MAGIC_KEY  = "Cal Magic"


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


# Manual overrides for clubs where the short team name doesn't share words with the club name
_TEAM_OVERRIDES = {
    "california magic": "Cal Magic 2012G West",
    "los angeles bulls": "LA Bulls G12 DPLO",
    "phoenix rush 2012": "Phoenix Rush Girls NL Premier 2",
}


def clean_team(name):
    """Strip the club prefix GotsPort prepends before the actual team name.

    GotsPort concatenates club display name + team name in the same cell,
    e.g. 'Las Vegas Storm FC Las Vegas Storm FC G12 Academy'.
    Strategy: detect a repeated word-prefix (case-insensitive) and return
    everything from the second occurrence onward.
    Falls back to stripping known club-name suffixes for abbreviation cases
    like 'California Magic Soccer Club Cal Magic 2012G West'.
    """
    name = name.strip()

    # Check hardcoded overrides first (for club/team abbreviation mismatches)
    lower = name.lower()
    for key, override in _TEAM_OVERRIDES.items():
        if lower.startswith(key):
            return override

    words = name.split()

    # Try to find a repeated prefix (handles most GotsPort cases)
    for i in range(1, len(words) // 2 + 1):
        prefix = " ".join(words[:i]).lower()
        rest   = " ".join(words[i:])
        if rest.lower().startswith(prefix):
            return rest.strip()

    # Fallback: strip common club-name suffixes then re-check for repeated prefix
    club_suffixes = [
        " Soccer Club", " Football Club", " Soccer", " FC", " SC", " United"
    ]
    short = name
    for suffix in club_suffixes:
        if suffix.lower() in short.lower():
            idx = short.lower().index(suffix.lower())
            candidate = (short[:idx] + short[idx + len(suffix):]).strip()
            if len(candidate) < len(name) - 3:
                short = candidate
                break

    # After stripping suffix, try repeated-prefix again on the shorter string
    if short != name:
        words2 = short.split()
        for i in range(1, len(words2) // 2 + 1):
            prefix = " ".join(words2[:i]).lower()
            rest   = " ".join(words2[i:])
            if rest.lower().startswith(prefix):
                return rest.strip()
        return short

    return name


def clean_time_location(raw):
    """Split a merged 'Mar 07, 20263:50 PM PSTField Change' cell into date, time, notes."""
    raw = raw.strip()
    # Extract date
    date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}', raw)
    date = date_match.group(0) if date_match else ""
    # Extract time
    time_match = re.search(r'(?<!\d)\d{1,2}:\d{2}\s*(AM|PM)\s*(PST|PDT|EST|EDT)?', raw)
    time = time_match.group(0).strip() if time_match else "TBD"
    return date, time


def parse_standings(soup):
    standings = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        if "PTS" not in headers or "Team" not in headers:
            continue
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cells or len(cells) < len(headers):
                continue
            entry = dict(zip(headers, cells))
            team = clean_team(entry.get("Team", ""))
            standings.append({
                "team":      team,
                "highlight": CAL_MAGIC_KEY in team,
                "mp":  entry.get("MP", "0"),
                "w":   entry.get("W",  "0"),
                "l":   entry.get("L",  "0"),
                "d":   entry.get("D",  "0"),
                "gf":  entry.get("GF", "0"),
                "ga":  entry.get("GA", "0"),
                "gd":  entry.get("GD", "0"),
                "pts": entry.get("PTS","0"),
            })
        if standings:
            break  # first matching table is the standings
    return standings


def parse_schedule(soup, cal_magic_only=False):
    """Parse schedule tables from a GotsPort page.

    cal_magic_only=True  → league view: only Cal Magic rows, W/L from her perspective
    cal_magic_only=False → tournament view: all rows, neutral score display
    """
    games = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        if "Home Team" not in headers:
            continue
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cells or len(cells) < 4:
                continue
            entry = dict(zip(headers, cells))
            date, time = clean_time_location(entry.get("Time", ""))
            home     = clean_team(entry.get("Home Team", ""))
            away     = clean_team(entry.get("Away Team", ""))
            result   = entry.get("Results", "-").strip()
            loc_raw  = entry.get("Location", "")
            location = loc_raw.split(" - ")[-1].strip() if " - " in loc_raw else loc_raw.strip()

            cal_home = CAL_MAGIC_KEY in home
            cal_away = CAL_MAGIC_KEY in away

            if cal_magic_only and not cal_home and not cal_away:
                continue

            score_match = re.search(r'(\d+)\s*-\s*(\d+)', result)
            status = "upcoming"
            result_label = ""

            if score_match:
                h_score, a_score = int(score_match.group(1)), int(score_match.group(2))
                status = "final"
                if cal_home or cal_away:
                    # Show W/L from Cal Magic's perspective
                    cal_score   = h_score if cal_home else a_score
                    other_score = a_score if cal_home else h_score
                    result_label = (f"W {cal_score}–{other_score}" if cal_score > other_score else
                                    f"D {cal_score}–{other_score}" if cal_score == other_score else
                                    f"L {cal_score}–{other_score}")
                else:
                    # Neutral score for non-Cal Magic games
                    result_label = f"{h_score}–{a_score}"

            games.append({
                "date":     date,
                "time":     time,
                "home":     home,
                "away":     away,
                "cal_home": cal_home,
                "cal_away": cal_away,
                "location": location,
                "result":   result_label,
                "status":   status,
            })
    return games


def get_league_data():
    soup = fetch(LEAGUE_URL)
    schedule = parse_schedule(soup, cal_magic_only=True)
    # Flatten to the shape the template expects
    flat = []
    for g in schedule:
        opponent = g["away"] if g["cal_home"] else g["home"]
        flat.append({
            "date":     g["date"],
            "time":     g["time"],
            "opponent": opponent,
            "location": g["location"],
            "result":   g["result"],
            "status":   g["status"],
        })
    return {
        "name":      "NorCal Premier Spring 2025–26",
        "division":  "Female U14 — Gold — Region 3/4 — Bracket A",
        "coach":     "Alfredo Rocha",
        "standings": parse_standings(soup),
        "schedule":  flat,
    }


def get_tournament_data():
    soup = fetch(TOURNAMENT_URL)
    # Tournament uses bracket standings — parse all standing tables
    all_brackets = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        if "PTS" not in headers or "Team" not in headers:
            continue
        bracket_rows = []
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cells:
                continue
            entry = dict(zip(headers, cells))
            team = clean_team(entry.get("Team", ""))
            bracket_rows.append({
                "team":      team,
                "highlight": CAL_MAGIC_KEY in team,
                "mp":  entry.get("MP", "0"),
                "w":   entry.get("W",  "0"),
                "l":   entry.get("L",  "0"),
                "d":   entry.get("D",  "0"),
                "gf":  entry.get("GF", "0"),
                "ga":  entry.get("GA", "0"),
                "gd":  entry.get("GD", "0"),
                "pts": entry.get("PTS","0"),
            })
        if bracket_rows:
            all_brackets.append(bracket_rows)

    brackets = [{"name": f"Bracket {'ABCDEFGH'[i]}", "standings": b} for i, b in enumerate(all_brackets)]
    schedule = parse_schedule(soup, cal_magic_only=False)
    results  = [g for g in schedule if g["status"] == "final"]
    upcoming = [g for g in schedule if g["status"] == "upcoming"]

    return {
        "name":     "Players College Showcase 2026",
        "location": "Las Vegas, NV",
        "dates":    "March 13–15, 2026",
        "division": "Female U14 — Red Rock Division",
        "brackets": brackets,
        "results":  results,
        "upcoming": upcoming,
    }
