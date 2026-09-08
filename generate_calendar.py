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

# Embedded Vector SVG Logos (Zero hotlinking restrictions, works everywhere)
SVG_LOGOS = {
    'KAYO': '''<svg viewBox="0 0 100 40" class="svg-logo"><rect width="100" height="40" rx="6" fill="#003366"/><text x="50" y="26" fill="#40F87F" font-family="Impact, sans-serif" font-size="20" font-weight="bold" text-anchor="middle">KAYO</text></svg>''',
    'FOXTEL': '''<svg viewBox="0 0 100 40" class="svg-logo"><rect width="100" height="40" rx="6" fill="#FF5000"/><text x="50" y="26" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="16" font-weight="900" text-anchor="middle">FOXTEL</text></svg>''',
    'CH7': '''<svg viewBox="0 0 60 40" class="svg-logo"><rect width="60" height="40" rx="6" fill="#ED1C24"/><text x="30" y="29" fill="#FFFFFF" font-family="Impact, sans-serif" font-size="28" font-weight="bold" text-anchor="middle">7</text></svg>''',
    'NINE': '''<svg viewBox="0 0 60 40" class="svg-logo"><rect width="60" height="40" rx="6" fill="#0099FF"/><circle cx="18" cy="20" r="4" fill="#FFF"/><circle cx="30" cy="20" r="4" fill="#FFF"/><circle cx="42" cy="20" r="4" fill="#FFF"/></svg>''',
    'ESPN': '''<svg viewBox="0 0 100 40" class="svg-logo"><rect width="100" height="40" rx="6" fill="#CC0000"/><text x="50" y="27" fill="#FFFFFF" font-family="Arial Black, sans-serif" font-size="20" font-style="italic" font-weight="900" text-anchor="middle">ESPN</text></svg>'''
}

sports_config = {
    'AFL': {'url': 'https://fixturedownload.com/feed/json/afl-2026', 'emoji': '🏈'},
    'NRL': {'url': 'https://fixturedownload.com/feed/json/nrl-2026', 'emoji': '🏉'}
}

all_games = []
now_utc = datetime.now(timezone.utc)
awst_tz = timezone(timedelta(hours=8))
two_weeks_ago = now_utc - timedelta(days=14)
two_weeks_ahead = now_utc + timedelta(days=14)

def get_broadcasters(sport, start_awst, full_title):
    """Assigns vector SVG logos based on league and local kick-off time."""
    logos = []
    
    if sport == 'AFL':
        logos.extend([SVG_LOGOS['KAYO'], SVG_LOGOS['FOXTEL']])
        weekday = start_awst.weekday() # 3=Thu, 4=Fri, 6=Sun
        if weekday in [3, 4, 6] or 'final' in full_title.lower():
            logos.append(SVG_LOGOS['CH7'])

    elif sport == 'NRL':
        logos.extend([SVG_LOGOS['KAYO'], SVG_LOGOS['FOXTEL']])
        weekday = start_awst.weekday()
        if weekday in [3, 4, 6] or 'final' in full_title.lower():
            logos.append(SVG_LOGOS['NINE'])

    elif sport == 'UFC':
        logos.extend([SVG_LOGOS['ESPN'], SVG_LOGOS['KAYO']])

    return "".join(logos)

def get_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-AU&gl=AU&ceid=AU:en"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            tree = ET.fromstring(response.read())
            items = tree.findall('.//item')[:2]
            return [{'title': i.find('title').text, 'link': i.find('link').text} for i in items]
    except Exception:
        return []

def format_round_name(round_val):
    if not round_val: return ""
    r_str = str(round_val).strip()
    low_r = r_str.lower()
    if 'grand final' in low_r: return "Grand Final"
    elif 'preliminary' in low_r or 'prelim' in low_r: return "Preliminary Final"
    elif 'semi' in low_r: return "Semi Final"
    elif 'elimination' in low_r: return "Elimination Final"
    elif 'qualifying' in low_r: return "Qualifying Final"
    elif 'final' in low_r: return f"Finals ({r_str.title()})"
    elif r_str.isdigit(): return f"Round {r_str}"
    return r_str

# --- 1. PROCESS AFL & NRL ---
for sport, config in sports_config.items():
    try:
        req = urllib.request.Request(config['url'], headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            for item in data:
                home = item.get('HomeTeam', '')
                away = item.get('AwayTeam', '')
                h_score = item.get('HomeTeamScore')
                a_score = item.get('AwayTeamScore')
                h_pos = f"({item.get('HomeTeamPosition')}th)" if item.get('HomeTeamPosition') else ""
                a_pos = f"({item.get('AwayTeamPosition')}th)" if item.get('AwayTeamPosition') else ""

                round_label = format_round_name(item.get('RoundNumber') or item.get('Round'))
                round_prefix = f"[{round_label}] " if round_label else ""

                if h_score is not None and a_score is not None:
                    h_val, a_val = int(h_score), int(a_score)
                    if h_val > a_val:
                        title = f"{config['emoji']} [{sport}] {round_prefix}🏆 {home} {h_pos} {h_val} - {a_val} {away} {a_pos} ❌"
                    elif a_val > h_val:
                        title = f"{config['emoji']} [{sport}] {round_prefix}❌ {home} {h_pos} {h_val} - {a_val} {away} {a_pos} 🏆"
                    else:
                        title = f"{config['emoji']} [{sport}] {round_prefix}🤝 {home} {h_pos} {h_val} - {a_val} {away} {a_pos}"
                else:
                    title = f"{config['emoji']} [{sport}] {round_prefix}{home} {h_pos} vs {away} {a_pos}".replace("  ", " ")

                date_str = item.get('DateUtc') or item.get('UtcDate')
                if not date_str: continue

                start_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                start_awst = start_utc.astimezone(awst_tz)

                # Store for ICS
                event = Event()
                event.add('uid', f"{sport.lower()}-{item.get('MatchNumber', '0')}-{home}")
                event.add('summary', title)
                event.add('dtstart', start_utc)
                event.add('dtend', datetime.fromtimestamp(start_utc.timestamp() + 9000, tz=timezone.utc))
                if item.get('Location'): event.add('location', item.get('Location'))
                cal.add_component(event)

                if two_weeks_ago <= start_utc <= two_weeks_ahead:
                    all_games.append({
                        'sport': sport,
                        'emoji': config['emoji'],
                        'full_title': title,
                        'date_awst': start_awst.strftime('%d/%m/%Y %H:%M AWST'),
                        'start_utc': start_utc,
                        'is_played': start_utc < now_utc and h_score is not None,
                        'location': item.get('Location', 'TBD'),
                        'broadcasters': get_broadcasters(sport, start_awst, title),
                        'odds_link': f"https://www.google.com/search?q={urllib.parse.quote(home + ' vs ' + away + ' odds')}",
                        'news': get_news(f"{home} {away} {sport}")
                    })
    except Exception as e:
        print(f"Error processing {sport}: {e}")

# --- 2. PROCESS UFC DATA ---
ufc_url = 'https://raw.githubusercontent.com/clarencechaan/ufc-cal/ics/UFC.ics'
try:
    req = urllib.request.Request(ufc_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        ufc_cal = Calendar.from_ical(response.read())
        for component in ufc_cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary'))
                clean_summary = summary.replace('[UFC]', '').replace('🥊', '').strip()
                full_summary = f"🥊 [UFC] {clean_summary}"

                component['summary'] = full_summary
                cal.add_component(component)

                dt_raw = component.get('dtstart').dt
                if isinstance(dt_raw, datetime):
                    dtstart_utc = dt_raw if dt_raw.tzinfo else dt_raw.replace(tzinfo=timezone.utc)
                else:
                    dtstart_utc = datetime.combine(dt_raw, datetime.min.time(), tzinfo=timezone.utc)

                dtstart_awst = dtstart_utc.astimezone(awst_tz)

                if two_weeks_ago <= dtstart_utc <= two_weeks_ahead:
                    all_games.append({
                        'sport': 'UFC',
                        'emoji': '🥊',
                        'full_title': full_summary,
                        'date_awst': dtstart_awst.strftime('%d/%m/%Y %H:%M AWST'),
                        'start_utc': dtstart_utc,
                        'is_played': dtstart_utc < now_utc,
                        'location': str(component.get('location', 'TBD')),
                        'broadcasters': get_broadcasters('UFC', dtstart_awst, full_summary),
                        'odds_link': f"https://www.google.com/search?q={urllib.parse.quote(clean_summary + ' odds')}",
                        'news': get_news(f"{clean_summary} UFC")
                    })
except Exception as e:
    print(f"Error fetching UFC: {e}")

all_games.sort(key=lambda x: x['start_utc'], reverse=True)

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
        .card {{ background: #1e1e1e; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #2ed573; position: relative; }}
        .card.played {{ border-left-color: #ff4d4d !important; }}
        .card.upcoming {{ border-left-color: #2ed573 !important; }}
        .card-header {{ font-size: 1.15em; font-weight: bold; margin-bottom: 10px; padding-right: 140px; }}
        .card-meta {{ color: #aaa; font-size: 0.9em; margin-bottom: 10px; }}
        
        .tv-logos {{ position: absolute; top: 15px; right: 15px; display: flex; gap: 6px; align-items: center; }}
        .svg-logo {{ height: 22px; width: auto; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.5)); }}

        .news-box {{ background: #2a2a2a; padding: 10px; border-radius: 5px; margin-top: 10px; }}
        .news-box a {{ color: #70a1ff; text-decoration: none; display: block; margin-bottom: 5px; }}
        .news-box a:hover {{ text-decoration: underline; }}
        .btn-odds {{ display: inline-block; padding: 5px 10px; background: #ffa500; color: #000; font-weight: bold; text-decoration: none; border-radius: 4px; font-size: 0.85em; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 🏉 🥊 Multi-Sport Live Hub</h1>
        <div class="subtitle">AWST (+08:00) | Green = Upcoming, Red = Played</div>
        <div id="games">
"""

for game in all_games:
    news_html = ""
    for article in game['news']:
        news_html += f'<a href="{article["link"]}" target="_blank">📰 {article["title"]}</a>'
    if not news_html:
        news_html = '<span style="color:#777;">No recent news articles found.</span>'

    status_class = "played" if game['is_played'] else "upcoming"

    html_content += f"""
        <div class="card {status_class}">
            <div class="tv-logos">{game['broadcasters']}</div>
            <div class="card-header">{game['full_title']}</div>
            <div class="card-meta">📅 {game['date_awst']} | 📍 {game['location']}</div>
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
