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


def clean_team(name):
    """Strip the club prefix GotsPort prepends (e.g. 'California Magic Soccer Club Cal Magic 2012G West')."""
    # GotsPort duplicates club name before team name — find the shorter repeated portion and remove it
    name = name.strip()
    # Remove known long prefixes
    prefixes = [
        "California Magic Soccer Club ",
        "Mt Diablo Mustang Soccer ",
        "Livermore Fusion SC ",
        "Association Football Club ",
        "Solano Surf ",
        "Revolution FC ",
        "1974 Newark FC ",
        "UC Premier ",
    ]
    for p in prefixes:
        if name.startswith(p):
            name = name[len(p):]
    return name.strip()


def clean_time_location(raw):
    """Split a merged 'Mar 07, 20263:50 PM PSTField Change' cell into date, time, notes."""
    raw = raw.strip()
    # Extract date
    date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}', raw)
    date = date_match.group(0) if date_match else ""
    # Extract time
    time_match = re.search(r'\d{1,2}:\d{2}\s*(AM|PM)\s*(PST|PDT|EST|EDT)?', raw)
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


def parse_schedule(soup):
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
            home    = clean_team(entry.get("Home Team", ""))
            away    = clean_team(entry.get("Away Team", ""))
            result  = entry.get("Results", "-").strip()
            location = entry.get("Location", "").split(" - ")[-1].strip() or entry.get("Location", "")

            # Determine if Cal Magic is home or away and what the result was
            cal_home = CAL_MAGIC_KEY in home
            cal_away = CAL_MAGIC_KEY in away
            if not cal_home and not cal_away:
                opponent = f"{home} vs {away}"
            else:
                opponent = away if cal_home else home

            # Parse score and result
            score_match = re.match(r'(\d+)\s*-\s*(\d+)', result)
            status = "upcoming"
            result_label = ""
            if score_match:
                h_score, a_score = int(score_match.group(1)), int(score_match.group(2))
                cal_score    = h_score if cal_home else a_score
                other_score  = a_score if cal_home else h_score
                result_label = f"W {cal_score}–{other_score}" if cal_score > other_score else (
                               f"D {cal_score}–{other_score}" if cal_score == other_score else
                               f"L {cal_score}–{other_score}")
                status = "final"

            games.append({
                "date":     date,
                "time":     time,
                "opponent": opponent,
                "location": location,
                "result":   result_label,
                "status":   status,
            })
    return games


def get_league_data():
    soup = fetch(LEAGUE_URL)
    # Get event name from page title/heading
    heading = soup.find("h1") or soup.find("title")
    name = heading.get_text(strip=True) if heading else "NorCal Premier Spring 2025–26"

    return {
        "name":      "NorCal Premier Spring 2025–26",
        "division":  "Female U14 — Gold — Region 3/4 — Bracket A",
        "coach":     "Alfredo Rocha",
        "standings": parse_standings(soup),
        "schedule":  parse_schedule(soup),
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
    schedule = parse_schedule(soup)
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
