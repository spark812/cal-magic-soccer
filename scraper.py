import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

TOURNAMENT_URL = "https://system.gotsport.com/org_event/events/44771/schedules?group=478899"
LEAGUE_URL = "https://system.gotsport.com/org_event/events/49370/schedules?team=3796059"


def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_standings(soup):
    standings = []
    # GotsPort standings tables have class patterns we look for
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        if not any(h in headers for h in ["Team", "PTS", "W", "MP"]):
            continue
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if cells and len(cells) >= 4:
                standings.append(dict(zip(headers, cells)))
    return standings


def parse_schedule(soup):
    games = []
    # Look for schedule/game rows — GotsPort uses various containers
    for row in soup.find_all(["tr", "div"], class_=lambda c: c and any(
        x in c for x in ["game", "match", "schedule", "event"]
    )):
        text = row.get_text(" ", strip=True)
        if text:
            games.append(text)
    return games


def get_tournament_data():
    try:
        soup = fetch_page(TOURNAMENT_URL)
        return {
            "standings": parse_standings(soup),
            "raw_html": str(soup.find("main") or soup.find("body")),
        }
    except Exception as e:
        return {"error": str(e)}


def get_league_data():
    try:
        soup = fetch_page(LEAGUE_URL)
        return {
            "standings": parse_standings(soup),
            "raw_html": str(soup.find("main") or soup.find("body")),
        }
    except Exception as e:
        return {"error": str(e)}
