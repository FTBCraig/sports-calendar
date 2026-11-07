import urllib.request
import urllib.parse
import json
import html
import xml.etree.ElementTree as ET
from icalendar import Calendar, Event
from datetime import datetime, timezone, timedelta

cal = Calendar()
cal.add('prodid', '-//Multi-Sport Consolidated Calendar//MX//')
cal.add('version', '2.0')
cal.add('x-wr-calname', 'AFL, NRL, UFC, F1, Rugby World Cup & NBA Finals')
cal.add('x-wr-timezone', 'Australia/Perth')
cal.add('x-published-ttl', 'PT12H')      # hint to calendar apps: re-check every 12 hrs
cal.add('refresh-interval', timedelta(hours=12), parameters={'VALUE': 'DURATION'})

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
    'ESPN': '''<svg viewBox="0 0 100 40" class="svg-logo"><rect width="100" height="40" rx="6" fill="#CC0000"/><text x="50" y="27" fill="#FFFFFF" font-family="Arial Black, sans-serif" font-size="20" font-style="italic" font-weight="900" text-anchor="middle">ESPN</text></svg>''',
    'STAN': '''<svg viewBox="0 0 100 40" class="svg-logo"><rect width="100" height="40" rx="6" fill="#0072CE"/><text x="50" y="27" fill="#FFFFFF" font-family="Arial Black, sans-serif" font-size="18" font-weight="900" text-anchor="middle">STAN</text></svg>''',
    'TEN': '''<svg viewBox="0 0 60 40" class="svg-logo"><rect width="60" height="40" rx="6" fill="#111111"/><text x="30" y="29" fill="#FFFFFF" font-family="Impact, sans-serif" font-size="26" font-weight="bold" text-anchor="middle">10</text></svg>''',
}

now_utc = datetime.now(timezone.utc)
awst_tz = timezone(timedelta(hours=8))
two_weeks_ago = now_utc - timedelta(days=14)
two_weeks_ahead = now_utc + timedelta(days=14)

# Fetch this year AND next year, so the calendar rolls into the new season by itself.
# (Feeds for next year that aren't published yet just get skipped.)
SEASONS = [now_utc.year, now_utc.year + 1]

sports_config = {
    'AFL': {'feed': 'afl', 'emoji': '🏈'},
    'NRL': {'feed': 'nrl', 'emoji': '🏉'},
}

all_games = []


def fetch(url, timeout=10, ua=None):
    h = dict(headers)
    if ua:
        h['User-Agent'] = ua
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_json(url, **kw):
    return json.loads(fetch(url, **kw).decode('utf-8'))


def get_broadcasters(sport, start_awst, full_title):
    """Assigns vector SVG logos based on league and local kick-off time."""
    logos = []
    low = full_title.lower()

    if sport == 'AFL':
        logos.extend([SVG_LOGOS['KAYO'], SVG_LOGOS['FOXTEL']])
        if start_awst.weekday() in [3, 4, 6] or 'final' in low:
            logos.append(SVG_LOGOS['CH7'])
    elif sport == 'NRL':
        logos.extend([SVG_LOGOS['KAYO'], SVG_LOGOS['FOXTEL']])
        if start_awst.weekday() in [3, 4, 6] or 'final' in low:
            logos.append(SVG_LOGOS['NINE'])
    elif sport == 'UFC':
        logos.extend([SVG_LOGOS['ESPN'], SVG_LOGOS['KAYO']])
    elif sport == 'F1':
        logos.extend([SVG_LOGOS['KAYO'], SVG_LOGOS['FOXTEL']])
        if 'australian grand prix' in low:   # Network 10 shows the home GP live
            logos.append(SVG_LOGOS['TEN'])
    elif sport == 'RWC':
        logos.extend([SVG_LOGOS['STAN'], SVG_LOGOS['NINE']])
    elif sport == 'NBA':
        logos.extend([SVG_LOGOS['ESPN'], SVG_LOGOS['KAYO'], SVG_LOGOS['FOXTEL']])

    return "".join(logos)


def get_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-AU&gl=AU&ceid=AU:en"
        tree = ET.fromstring(fetch(url, timeout=5))
        items = tree.findall('.//item')[:2]
        return [{'title': i.find('title').text, 'link': i.find('link').text} for i in items]
    except Exception:
        return []


FINALS_NAMES = {
    # fixturedownload only gives round numbers, so finals are named in order after the last
    # normal round (a normal round has 5+ games; finals rounds have 4 or fewer).
    'AFL': ["Wildcard Round", "Finals Week 1", "Semi Finals", "Preliminary Finals", "Grand Final"],
    'NRL': ["Finals Week 1", "Semi Finals", "Preliminary Finals", "Grand Final"],
}


def build_round_labels(sport, data):
    counts = {}
    for i in data:
        r = str(i.get('RoundNumber', ''))
        if r.isdigit():
            counts[int(r)] = counts.get(int(r), 0) + 1
    labels = {r: ("Opening Round" if r == 0 else f"Round {r}") for r in counts}
    normal = [r for r, c in counts.items() if c >= 5]
    if normal:
        finals = sorted(r for r in counts if r > max(normal))
        names = FINALS_NAMES.get(sport, [])
        # AFL wildcard round has 2 games; if the first finals round has 4, there's no wildcard round
        if sport == 'AFL' and finals and counts[finals[0]] >= 4:
            names = names[1:]
        for idx, r in enumerate(finals):
            if idx < len(names):
                labels[r] = names[idx]
    return labels


def add_game(sport, emoji, title, start_utc, duration_mins, uid, location='', played=False,
             search_term='', news_query=''):
    """Adds one event to the .ics and, if within +/- 2 weeks, to the web page."""
    event = Event()
    event.add('uid', uid)
    event.add('summary', title)
    event.add('dtstart', start_utc)
    event.add('dtend', start_utc + timedelta(minutes=duration_mins))
    event.add('dtstamp', now_utc)
    if location:
        event.add('location', location)
    cal.add_component(event)

    if two_weeks_ago <= start_utc <= two_weeks_ahead:
        start_awst = start_utc.astimezone(awst_tz)
        all_games.append({
            'sport': sport,
            'emoji': emoji,
            'full_title': title,
            'date_awst': start_awst.strftime('%a %d/%m/%Y %H:%M AWST'),
            'start_utc': start_utc,
            'is_played': played or start_utc + timedelta(minutes=duration_mins) < now_utc,
            'location': location or 'TBD',
            'broadcasters': get_broadcasters(sport, start_awst, title),
            'odds_link': f"https://www.google.com/search?q={urllib.parse.quote((search_term or title) + ' odds')}",
            'news': get_news(news_query or search_term or title),
        })


def score_title(prefix, home, away, h_score, a_score):
    """'prefix 🏆 Home 100 - 80 Away ❌' if there's a score, otherwise 'prefix Home vs Away'."""
    if h_score is None or a_score is None or h_score == '' or a_score == '':
        return f"{prefix}{home} vs {away}"
    h_val, a_val = int(h_score), int(a_score)
    if h_val > a_val:
        return f"{prefix}🏆 {home} {h_val} - {a_val} {away} ❌"
    if a_val > h_val:
        return f"{prefix}❌ {home} {h_val} - {a_val} {away} 🏆"
    return f"{prefix}🤝 {home} {h_val} - {a_val} {away}"


# --- 1. AFL & NRL (fixturedownload.com) ---
for sport, config in sports_config.items():
    for year in SEASONS:
        url = f"https://fixturedownload.com/feed/json/{config['feed']}-{year}"
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"Skipping {sport} {year}: {e}")
            continue

        labels = build_round_labels(sport, data)

        for item in data:
            date_str = item.get('DateUtc') or item.get('UtcDate')
            if not date_str:
                continue
            start_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00').replace(' ', 'T'))
            if start_utc.tzinfo is None:
                start_utc = start_utc.replace(tzinfo=timezone.utc)

            home = item.get('HomeTeam', '')
            away = item.get('AwayTeam', '')
            h_score = item.get('HomeTeamScore')
            a_score = item.get('AwayTeamScore')
            label = labels.get(int(item['RoundNumber']), '') if str(item.get('RoundNumber', '')).isdigit() else str(item.get('RoundNumber') or '')
            prefix = f"{config['emoji']} [{sport}] " + (f"[{label}] " if label else "")

            add_game(
                sport, config['emoji'],
                score_title(prefix, home, away, h_score, a_score),
                start_utc, 150,
                uid=f"{sport.lower()}-{year}-{item.get('MatchNumber', '0')}",
                location=item.get('Location', ''),
                played=h_score is not None,
                search_term=f"{home} vs {away}",
                news_query=f"{home} {away} {sport}",
            )

# --- 2. UFC (community .ics feed) ---
ufc_url = 'https://raw.githubusercontent.com/clarencechaan/ufc-cal/ics/UFC.ics'
try:
    ufc_cal = Calendar.from_ical(fetch(ufc_url))
    for component in ufc_cal.walk():
        if component.name != "VEVENT":
            continue
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

        if two_weeks_ago <= dtstart_utc <= two_weeks_ahead:
            dtstart_awst = dtstart_utc.astimezone(awst_tz)
            all_games.append({
                'sport': 'UFC',
                'emoji': '🥊',
                'full_title': full_summary,
                'date_awst': dtstart_awst.strftime('%a %d/%m/%Y %H:%M AWST'),
                'start_utc': dtstart_utc,
                'is_played': dtstart_utc < now_utc,
                'location': str(component.get('location', 'TBD')),
                'broadcasters': get_broadcasters('UFC', dtstart_awst, full_summary),
                'odds_link': f"https://www.google.com/search?q={urllib.parse.quote(clean_summary + ' odds')}",
                'news': get_news(f"{clean_summary} UFC"),
            })
except Exception as e:
    print(f"Error fetching UFC: {e}")

# --- 3. F1 (Jolpica API, the free replacement for Ergast) ---
F1_UA = 'sports-calendar/1.0 (+https://github.com/FTBCraig/sports-calendar)'
F1_SESSIONS = [  # (json key, label, length in minutes)
    ('SprintQualifying', 'Sprint Qualifying', 60),
    ('Sprint', 'Sprint', 60),
    ('Qualifying', 'Qualifying', 60),
]


def f1_time(date_s, time_s):
    if not time_s:
        time_s = '00:00:00Z'
    return datetime.fromisoformat(f"{date_s}T{time_s}".replace('Z', '+00:00'))


for year in SEASONS:
    try:
        races = fetch_json(f"https://api.jolpi.ca/ergast/f1/{year}.json?limit=100", ua=F1_UA)['MRData']['RaceTable']['Races']
    except Exception as e:
        print(f"Skipping F1 {year}: {e}")
        continue

    winners = {}
    try:
        res = fetch_json(f"https://api.jolpi.ca/ergast/f1/{year}/results/1.json?limit=100", ua=F1_UA)
        for r in res['MRData']['RaceTable']['Races']:
            d = r['Results'][0]['Driver']
            winners[r['round']] = f"{d['givenName']} {d['familyName']}"
    except Exception as e:
        print(f"Could not get F1 {year} winners: {e}")

    for race in races:
        name = race['raceName']
        rnd = race['round']
        circuit = race.get('Circuit', {})
        loc = circuit.get('Location', {})
        location = f"{circuit.get('circuitName', '')}, {loc.get('locality', '')}, {loc.get('country', '')}".strip(', ')

        for key, label, mins in F1_SESSIONS:
            s = race.get(key)
            if s and s.get('date'):
                add_game('F1', '🏎️', f"🏎️ [F1] {name} – {label}", f1_time(s['date'], s.get('time')), mins,
                         uid=f"f1-{year}-{rnd}-{key.lower()}", location=location,
                         search_term=f"F1 {name} {year}")

        race_title = f"🏎️ [F1] [Round {rnd}] {name}"
        if rnd in winners:
            race_title += f" – 🏆 {winners[rnd]}"
        add_game('F1', '🏎️', race_title, f1_time(race['date'], race.get('time')), 120,
                 uid=f"f1-{year}-{rnd}-race", location=location, played=rnd in winners,
                 search_term=f"F1 {name} {year}")

# --- 4. Rugby World Cup & NBA Finals (ESPN public scoreboard API) ---
def espn_events(url):
    try:
        return fetch_json(url).get('events', [])
    except Exception as e:
        print(f"Skipping {url}: {e}")
        return []


def espn_game(ev, sport, emoji, prefix, duration):
    comp = (ev.get('competitions') or [{}])[0]
    teams = {c.get('homeAway'): c for c in comp.get('competitors', [])}
    home, away = teams.get('home', {}), teams.get('away', {})
    h_name = home.get('team', {}).get('displayName', 'TBD')
    a_name = away.get('team', {}).get('displayName', 'TBD')
    done = comp.get('status', ev.get('status', {})).get('type', {}).get('completed', False)
    h_score = home.get('score') if done else None
    a_score = away.get('score') if done else None
    venue = comp.get('venue', {})
    city = venue.get('address', {}).get('city', '')
    location = ", ".join(x for x in [venue.get('fullName', ''), city] if x)
    start_utc = datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))

    add_game(sport, emoji, score_title(prefix, h_name, a_name, h_score, a_score), start_utc, duration,
             uid=f"{sport.lower()}-{ev.get('id')}", location=location, played=done,
             search_term=f"{h_name} vs {a_name}", news_query=f"{h_name} {a_name} {sport}")


# Rugby World Cup (men's) – ESPN league 164205. Next one: Australia, Oct–Nov 2027.
for year in SEASONS:
    for ev in espn_events(f"https://site.api.espn.com/apis/site/v2/sports/rugby/164205/scoreboard?dates={year}&limit=200"):
        espn_game(ev, 'RWC', '🏉', '🏉 [Rugby World Cup] ', 120)

# NBA Finals only – pull May & June playoff games and keep the ones labelled "NBA Finals".
for year in SEASONS:
    for month in ('05', '06'):
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={year}{month}&seasontype=3&limit=300"
        for ev in espn_events(url):
            headline = " ".join(n.get('headline', '') for n in ev.get('notes', []))
            if 'NBA Finals' not in headline:
                continue
            game_no = headline.split('NBA Finals')[-1].strip(' -') or ''
            prefix = f"🏀 [NBA Finals{(' ' + game_no) if game_no else ''}] "
            espn_game(ev, 'NBA', '🏀', prefix, 150)

# Upcoming (soonest first) at the top, then results (most recent first)
upcoming = sorted([g for g in all_games if not g['is_played']], key=lambda x: x['start_utc'])
played = sorted([g for g in all_games if g['is_played']], key=lambda x: x['start_utc'], reverse=True)
all_games = upcoming + played

with open('sports_master.ics', 'wb') as f:
    f.write(cal.to_ical())

# --- 5. BUILD HTML WEB PAGE ---
esc = html.escape
updated = now_utc.astimezone(awst_tz).strftime('%a %d/%m/%Y %H:%M AWST')

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
        .card-header {{ font-size: 1.15em; font-weight: bold; margin-bottom: 10px; padding-right: 160px; }}
        .card-meta {{ color: #aaa; font-size: 0.9em; margin-bottom: 10px; }}
        .tv-logos {{ position: absolute; top: 15px; right: 15px; display: flex; gap: 6px; align-items: center; }}
        .svg-logo {{ height: 22px; width: auto; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.5)); }}
        .news-box {{ background: #2a2a2a; padding: 10px; border-radius: 5px; margin-top: 10px; }}
        .news-box a {{ color: #70a1ff; text-decoration: none; display: block; margin-bottom: 5px; }}
        .news-box a:hover {{ text-decoration: underline; }}
        .btn-odds {{ display: inline-block; padding: 5px 10px; background: #ffa500; color: #000; font-weight: bold; text-decoration: none; border-radius: 4px; font-size: 0.85em; margin-top: 5px; }}
        .empty {{ text-align:center; color:#777; padding: 40px 0; }}
        @media (max-width: 600px) {{
            body {{ padding: 12px; }}
            .tv-logos {{ position: static; margin-bottom: 8px; }}
            .card-header {{ padding-right: 0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 🏉 🥊 🏎️ 🏀 Multi-Sport Live Hub</h1>
        <div class="subtitle">AWST (+08:00) | Green = Upcoming, Red = Played | Updated {updated}</div>
        <div id="games">
"""

if not all_games:
    html_content += '<div class="empty">Nothing on in the last or next 2 weeks.</div>'

for game in all_games:
    news_html = ""
    for article in game['news']:
        news_html += f'<a href="{esc(article["link"] or "")}" target="_blank" rel="noopener">📰 {esc(article["title"] or "")}</a>'
    if not news_html:
        news_html = '<span style="color:#777;">No recent news articles found.</span>'

    status_class = "played" if game['is_played'] else "upcoming"

    html_content += f"""
        <div class="card {status_class}">
            <div class="tv-logos">{game['broadcasters']}</div>
            <div class="card-header">{esc(game['full_title'])}</div>
            <div class="card-meta">📅 {game['date_awst']} | 📍 {esc(game['location'])}</div>
            <a href="{esc(game['odds_link'])}" target="_blank" rel="noopener" class="btn-odds">📈 View Live Odds</a>
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
