import urllib.request
import json
import xml.etree.ElementTree as ET
from icalendar import Calendar, Event
from datetime import datetime, timezone, timedelta

cal = Calendar()
cal.add('prodid', '-//Multi-Sport Consolidated Calendar//MX//')
cal.add('version', '2.0')
cal.add('x-wr-calname', 'AFL, NRL & UFC Events')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
}

sports_config = {
    'AFL': {'url': 'https://fixturedownload.com/feed/json/afl-2026', 'emoji': '🏈'},
    'NRL': {'url': 'https://fixturedownload.com/feed/json/nrl-2026', 'emoji': '🏉'}
}

all_games = []
now = datetime.now(timezone.utc)
two_weeks_ago = now - timedelta(days=14)
two_weeks_ahead = now + timedelta(days=14)

def get_news(query):
    """Fetches top 2 news headlines from Google News RSS."""
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-AU&gl=AU&ceid=AU:en"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            tree = ET.fromstring(response.read())
            items = tree.findall('.//item')[:2]
            return [{'title': i.find('title').text, 'link': i.find('link').text} for i in items]
    except Exception:
        return []

# --- 1. PROCESS AFL & NRL ---
for sport, config in sports_config.items():
    try:
        req = urllib.request.Request(config['url'], headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"Fetched {len(data)} items for {sport}")
            for item in data:
                home = item.get('HomeTeam', '')
                away = item.get('AwayTeam', '')
                h_score = item.get('HomeTeamScore')
                a_score = item.get('AwayTeamScore')
                h_pos = f"({item.get('HomeTeamPosition')}th)" if item.get('HomeTeamPosition') else ""
                a_pos = f"({item.get('AwayTeamPosition')}th)" if item.get('AwayTeamPosition') else ""

                if h_score is not None and a_score is not None:
                    h_val, a_val = int(h_score), int(a_score)
                    if h_val > a_val:
                        title = f"{config['emoji']} [{sport}] 🏆 {home} {h_pos} {h_val} - {a_val} {away} {a_pos} ❌"
                    elif a_val > h_val:
                        title = f"{config['emoji']} [{sport}] ❌ {home} {h_pos} {h_val} - {a_val} {away} {a_pos} 🏆"
                    else:
                        title = f"{config['emoji']} [{sport}] 🤝 {home} {h_pos} {h_val} - {a_val} {away} {a_pos}"
                else:
                    title = f"{config['emoji']} [{sport}] {home} {h_pos} vs {away} {a_pos}".replace("  ", " ")

                date_str = item.get('DateUtc') or item.get('UtcDate')
                if not date_str:
                    continue

                start = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Store for ICS Master Calendar
                event = Event()
                event.add('uid', f"{sport.lower()}-{item.get('MatchNumber', '0')}-{home}")
                event.add('summary', title)
                event.add('dtstart', start)
                event.add('dtend', datetime.fromtimestamp(start.timestamp() + 9000, tz=timezone.utc))
                if item.get('Location'):
                    event.add('location', item.get('Location'))
                cal.add_component(event)

                # Filter for Web Dashboard: -14 Days to +14 Days
                if two_weeks_ago <= start <= two_weeks_ahead:
                    all_games.append({
                        'sport': sport,
                        'emoji': config['emoji'],
                        'title': f"{home} vs {away}",
                        'full_title': title,
                        'date': start.strftime('%Y-%m-%d %H:%M UTC'),
                        'start_dt': start,
                        'location': item.get('Location', 'TBD'),
                        'odds_link': f"https://www.google.com/search?q={urllib.parse.quote(home + ' vs ' + away + ' odds')}",
                        'news': get_news(f"{home} {away} {sport}")
                    })
    except Exception as e:
        print(f"Error processing {sport}: {e}")

# --- 2. PROCESS UFC DATA ---
# Using backup working endpoint
ufc_feed_urls = [
    'https://raw.githubusercontent.com/f1cal/ufc/main/ufc-calendar.ics',
    'https://raw.githubusercontent.com/clarencechaan/ufc-cal/ics/UFC.ics'
]

ufc_success = False
for ufc_feed_url in ufc_feed_urls:
    try:
        req = urllib.request.Request(ufc_feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            ufc_cal = Calendar.from_ical(response.read())
            count = 0
            for component in ufc_cal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get('summary'))
                    clean_summary = summary.replace('[UFC]', '').replace('🥊', '').strip()
                    full_summary = f"🥊 [UFC] {clean_summary}"
                    
                    component['summary'] = full_summary
                    cal.add_component(component)
                    count += 1
                    
                    # Parse start date
                    dtstart = component.get('dtstart').dt
                    if not isinstance(dtstart, datetime):
                        dtstart = datetime.combine(dtstart, datetime.min.time(), tzinfo=timezone.utc)
                    elif dtstart.tzinfo is None:
                        dtstart = dtstart.replace(tzinfo=timezone.utc)

                    # Filter for Web Dashboard: -14 Days to +14 Days
                    if two_weeks_ago <= dtstart <= two_weeks_ahead:
                        all_games.append({
                            'sport': 'UFC',
                            'emoji': '🥊',
                            'title': clean_summary,
                            'full_title': full_summary,
                            'date': dtstart.strftime('%Y-%m-%d %H:%M UTC'),
                            'start_dt': dtstart,
                            'location': str(component.get('location', 'TBD')),
                            'odds_link': f"https://www.google.com/search?q={urllib.parse.quote(clean_summary + ' odds')}",
                            'news': get_news(f"{clean_summary} UFC")
                        })
            print(f"Successfully processed {count} UFC events from {ufc_feed_url}")
            ufc_success = True
            break
    except Exception as e:
        print(f"Failed to fetch UFC from {ufc_feed_url}: {e}")

# Sort Web Dashboard games DESCENDING (Newest/Future first, Past games last)
all_games.sort(key=lambda x: x['start_dt'], reverse=True)

# Save Master ICS File
with open('sports_master.ics', 'wb') as f:
    f.write(cal.to_ical())

# --- 3. BUILD HTML WEB PAGE ---
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Sport Live Hub</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #fff; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom:5px; }}
        .subtitle {{ text-align:center; color:#aaa; font-size:0.9em; margin-bottom:25px; }}
        .card {{ background: #1e1e1e; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 5px solid #007bff; }}
        .card.AFL {{ border-color: #ff4757; }}
        .card.NRL {{ border-color: #2ed573; }}
        .card.UFC {{ border-color: #ffa500; }}
        .card-header {{ font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }}
        .card-meta {{ color: #aaa; font-size: 0.9em; margin-bottom: 10px; }}
        .news-box {{ background: #2a2a2a; padding: 10px; border-radius: 5px; margin-top: 10px; }}
        .news-box a {{ color: #70a1ff; text-decoration: none; display: block; margin-bottom: 5px; }}
        .news-box a:hover {{ text-decoration: underline; }}
        .btn-odds {{ display: inline-block; padding: 5px 10px; background: #ffa500; color: #000; font-weight: bold; text-decoration: none; border-radius: 4px; font-size: 0.85em; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 🏉 🥊 Multi-Sport Live Hub</h1>
        <div class="subtitle">Showing matches from past 2 weeks & next 2 weeks (Descending)</div>
        <div id="games">
"""

for game in all_games:
    news_html = ""
    for article in game['news']:
        news_html += f'<a href="{article["link"]}" target="_blank">📰 {article["title"]}</a>'
    if not news_html:
        news_html = '<span style="color:#777;">No recent news articles found.</span>'

    html_content += f"""
        <div class="card {game['sport']}">
            <div class="card-header">{game['full_title']}</div>
            <div class="card-meta">📅 {game['date']} | 📍 {game['location']}</div>
            <a href="{game['odds_link']}" target="_blank" class="btn-odds">📈 View Live Odds</a>
            <div class="news-box">
                <strong>Latest News:</strong><br>
                {news_html}
            </div>
        </div>
    """

html_content += """
        </div>
    </div>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
