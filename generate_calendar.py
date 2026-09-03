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
    event.add('uid', str(uid))
    event.add('summary', str(summary))
    event.add('dtstart', start_time)
    event.add('dtend', end_time)
    if location:
        event.add('location', str(location))
    if description:
        event.add('description', str(description))
    cal.add_component(event)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}

# --- 1. AFL & NRL DATA ---
sports_config = {
    'AFL': {
        'url': 'https://fixturedownload.com/feed/json/afl-2026',
        'emoji': '🏈'
    },
    'NRL': {
        'url': 'https://fixturedownload.com/feed/json/nrl-2026',
        'emoji': '🏉'
    }
}

for sport, config in sports_config.items():
    try:
        req = urllib.request.Request(config['url'], headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"Successfully fetched {len(data)} items for {sport}")
            for item in data:
                match_id = f"{sport.lower()}-{item.get('MatchNumber', '0')}-{item.get('HomeTeam', '')}"
                
                home_team = item.get('HomeTeam', '')
                away_team = item.get('AwayTeam', '')
                
                # Fetch scores & ladder positions if present in feed
                h_score = item.get('HomeTeamScore')
                a_score = item.get('AwayTeamScore')
                h_pos = f"({item.get('HomeTeamPosition')}th)" if item.get('HomeTeamPosition') else ""
                a_pos = f"({item.get('AwayTeamPosition')}th)" if item.get('AwayTeamPosition') else ""

                # Format title based on match completion state
                if h_score is not None and a_score is not None:
                    try:
                        h_val = int(h_score)
                        a_val = int(a_score)
                        if h_val > a_val:
                            title = f"{config['emoji']} [{sport}] 🏆 {home_team} {h_pos} {h_val} - {a_val} {away_team} {a_pos} ❌"
                        elif a_val > h_val:
                            title = f"{config['emoji']} [{sport}] ❌ {home_team} {h_pos} {h_val} - {a_val} {away_team} {a_pos} 🏆"
                        else:
                            title = f"{config['emoji']} [{sport}] 🤝 {home_team} {h_pos} {h_val} - {a_val} {away_team} {a_pos}"
                    except ValueError:
                        title = f"{config['emoji']} [{sport}] {home_team} {h_pos} vs {away_team} {a_pos}"
                else:
                    title = f"{config['emoji']} [{sport}] {home_team} {h_pos} vs {away_team} {a_pos}".replace("  ", " ")

                date_str = item.get('DateUtc') or item.get('UtcDate')
                if not date_str:
                    continue
                    
                utc_str = date_str.replace('Z', '+00:00')
                start = datetime.fromisoformat(utc_str)
                end = datetime.fromtimestamp(start.timestamp() + 9000, tz=timezone.utc)
                
                add_event(
                    uid=match_id,
                    summary=title,
                    start_time=start,
                    end_time=end,
                    location=item.get('Location', '')
                )
    except Exception as e:
        print(f"Error processing {sport}: {e}")

# --- 2. UFC DATA ---
ufc_feed_url = 'https://raw.githubusercontent.com/clarencechaan/ufc-cal/ics/UFC.ics'
try:
    req = urllib.request.Request(ufc_feed_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        ufc_cal = Calendar.from_ical(response.read())
        for component in ufc_cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary'))
                clean_summary = summary.replace('[UFC]', '').strip()
                component['summary'] = f"🥊 [UFC] {clean_summary}"
                cal.add_component(component)
except Exception as e:
    print(f"Error fetching UFC: {e}")

# Save master .ics output
with open('sports_master.ics', 'wb') as f:
    f.write(cal.to_ical())
