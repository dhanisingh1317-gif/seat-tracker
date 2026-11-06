import json, os, re, time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

URL = "https://testcisia.it/calendario.php?tolc=cents&l=gb&lingua=inglese"
# Only track these? Put words that appear in the university/city name, e.g. ["Siena", "Udine"]. Empty list = track everything.
WATCH = []
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
DATA = "docs/data.json"


def fetch_rows():
    html = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        c = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) < 8:
            continue
        fmt, uni, region, city, deadline, seats, state, date = c[:8]
        if "UNI" not in fmt.upper():
            continue
        if WATCH and not any(w.lower() in (uni + " " + city).lower() for w in WATCH):
            continue
        if WATCH and not any(w.lower() in (uni + " " + city).lower() for w in WATCH):
            continue
        rows.append({
            "format": fmt, "university": uni, "region": region, "city": city,
            "deadline": deadline, "seats": seats, "state": state, "date": date,
            "open": state.upper().startswith("AVAILABLE"),
        })
    return rows


def key(r):
    return f'{r["format"]}|{r["university"]}|{r["date"]}'


def notify(msg):
    print(msg)
    if not NTFY_TOPIC:
        return
    for i in range(6):
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode("utf-8"),
                      headers={"Title": "CEnT-S HOME seat open!", "Priority": "urgent", "Click": URL})
        time.sleep(5)


def main():
    rows = fetch_rows()
    if not rows:
        print("No rows parsed - page layout may have changed. Leaving data untouched.")
        return

    old = {"rows": []}
    if os.path.exists(DATA):
        old = json.load(open(DATA, encoding="utf-8"))
    was_open = {key(r) for r in old["rows"] if r["open"]}

    for r in rows:
        if r["open"] and key(r) not in was_open:
            notify(f'{r["university"]} ({r["city"]}) - {r["date"]} - {r["seats"]} seats. Book now!')

    if rows != old["rows"]:
        os.makedirs("docs", exist_ok=True)
        out = {"changed": datetime.now(timezone.utc).isoformat(), "rows": rows}
        json.dump(out, open(DATA, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


main()
