import urllib.request
import json
import xml.etree.ElementTree as ET
from icalendar import Calendar, Event
from datetime import datetime, timezone

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

def get_news(query):
    """Fetches top 2 news headlines from Google News RSS."""
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-AU&gl=AU&ceid=AU:en"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            tree = ET.fromstring(response.read())
            items = tree.findall('.//item')[:2]
            return [{'title': i.find('title').text, 'link': i.find('link').text} for i in items]
    except Exception:
        return []

# 1. PROCESS AFL & NRL
for sport, config in sports_config.items():
    try:
        req = urllib.request.Request(config['url'], headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
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
                
                # Store for Web View
                all_games.append({
                    'sport': sport,
                    'emoji': config['emoji'],
                    'title': f"{home} vs {away}",
                    'full_title': title,
                    'date': start.strftime('%Y-%m-%d %H:%M UTC'),
                    'location': item.get('Location', 'TBD'),
                    'odds_link': f"https://www.google.com/search?q={urllib.parse.quote(home + ' vs ' + away + ' odds')}",
                    'news': get_news(f"{home} {away} {sport}")
                })

                # Store for ICS
                event = Event()
                event.add('uid', f"{sport.lower()}-{item.get('MatchNumber', '0')}-{home}")
                event.add('summary', title)
                event.add('dtstart', start)
                event.add('dtend', datetime.fromtimestamp(start.timestamp() + 9000, tz=timezone.utc))
                if item.get('Location'):
                    event.add('location', item.get('Location'))
                cal.add_component(event)
    except Exception as e:
        print(f"Error processing {sport}: {e}")

# Save ICS File
with open('sports_master.ics', 'wb') as f:
    f.write(cal.to_ical())

# 2. BUILD HTML WEB PAGE
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Sport Live Hub</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #fff; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .card {{ background: #1e1e1e; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 5px solid #007bff; }}
        .card.AFL {{ border-color: #ff4757; }}
        .card.NRL {{ border-color: #2ed573; }}
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
        <h1>🏈 🏉 Live Sports Dashboard</h1>
        <p style="text-align:center; color:#aaa;">Auto-updated every 12 hours</p>
        <div id="games">
"""

for game in all_games[:50]:  # Limits to upcoming 50 games for clean layout
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
