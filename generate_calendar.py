import urllib.request
import json
from icalendar import Calendar, Event
from datetime import datetime, timezone

cal = Calendar()
cal.add('prodid', '-//Multi-Sport Consolidated Calendar//MX//')
cal.add('version', '2.0')
cal.add('x-wr-calname', 'AFL, NRL & UFC Events')

def add_event(uid, summary, start_time, end_time, location="", description=""):
    event = Event()
    event.add('uid', uid)
    event.add('summary', summary)
    event.add('dtstart', start_time)
    event.add('dtend', end_time)
    if location:
        event.add('location', location)
    if description:
        event.add('description', description)
    cal.add_component(event)

# --- 1. AFL & NRL DATA (Sourced via FixtureDownload JSON API) ---
sports_urls = {
    'AFL': 'https://fixturedownload.com/feed/json/afl-2026',
    'NRL': 'https://fixturedownload.com/feed/json/nrl-2026'
}

for sport, url in sports_urls.items():
    try:
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode('utf-8'))
        for item in data:
            match_id = f"{sport.lower()}-{item['MatchNumber']}"
            title = f"[{sport}] {item['HomeTeam']} vs {item['AwayTeam']}"
            
            # Parse UTC ISO strings
            start = datetime.fromisoformat(item['UtcDate'].replace('Z', '+00:00'))
            # Approximate match duration to 2.5 hrs
            end = datetime.fromtimestamp(start.timestamp() + 9000, tz=timezone.utc)
            
            add_event(
                uid=match_id,
                summary=title,
                start_time=start,
                end_time=end,
                location=item.get('Location', '')
            )
    except Exception as e:
        print(f"Error fetching {sport}: {e}")

# --- 2. UFC DATA ---
ufc_feed_url = 'https://raw.githubusercontent.com/clarencechaan/ufc-cal/ics/UFC.ics'
try:
    req = urllib.request.urlopen(ufc_feed_url)
    ufc_cal = Calendar.from_ical(req.read())
    for component in ufc_cal.walk():
        if component.name == "VEVENT":
            component['summary'] = f"[UFC] {component.get('summary')}"
            cal.add_component(component)
except Exception as e:
    print(f"Error fetching UFC: {e}")

# Write to file
with open('sports_master.ics', 'wb') as f:
    f.write(cal.to_ical())
