# sports-calendar
AFL, NRL, UFC, F1, Rugby World Cup and NBA Finals in one .ics calendar, plus a web page with the
last and next 2 weeks of games. Refreshes every 12 hrs via GitHub Actions and publishes to GitHub Pages.

- Calendar feed: `sports_master.ics` (subscribe to it in Google/Apple/Outlook calendar)
- Web page: `index.html`

Data sources: fixturedownload.com (AFL, NRL), clarencechaan/ufc-cal (UFC), Jolpica API (F1),
ESPN public scoreboard (Rugby World Cup, NBA Finals). Seasons roll over automatically each year.
