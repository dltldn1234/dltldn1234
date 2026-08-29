#!/usr/bin/env python3
"""Generate the SIWOO.SYSTEM GitHub signal panel from GitHub GraphQL data."""

import html
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USER = "dltldn1234"
OUTPUT = Path("assets/github-signal.svg")
API_URL = "https://api.github.com/graphql"


def graphql(query, variables):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to read contribution data.")
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "siwoo-system-profile",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + result["errors"][0]["message"])
    return result["data"]


YEARS_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    contributionsCollection {
      contributionYears
    }
  }
}
"""

CALENDAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_contributions():
    identity = graphql(YEARS_QUERY, {"login": USER})["user"]
    years = identity["contributionsCollection"]["contributionYears"]
    if not years:
        raise RuntimeError("GitHub returned no contribution years for the configured user.")

    daily = {}
    total = 0
    for year in years:
        end = (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if year == date.today().year
            else f"{year}-12-31T23:59:59Z"
        )
        calendar = graphql(
            CALENDAR_QUERY,
            {
                "login": USER,
                "from": f"{year}-01-01T00:00:00Z",
                "to": end,
            },
        )["user"]["contributionsCollection"]["contributionCalendar"]
        total += calendar["totalContributions"]
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                day_date = date.fromisoformat(day["date"])
                if day_date.year == year:
                    daily[day_date] = day["contributionCount"]
    return identity["login"], total, daily


def streaks(daily):
    if not daily:
        return 0, 0
    first, last = min(daily), max(daily)
    longest = run = 0
    cursor = first
    while cursor <= last:
        if daily.get(cursor, 0) > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        cursor += timedelta(days=1)

    cursor = date.today()
    if daily.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    current = 0
    while daily.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def cell_color(count, peak):
    if count <= 0:
        return "#050B12"
    ratio = count / max(peak, 1)
    if ratio < 0.25:
        return "#14324A"
    if ratio < 0.5:
        return "#007AFF"
    if ratio < 0.75:
        return "#00AAFF"
    return "#34C759"


def render_svg(login, total, daily):
    current, longest = streaks(daily)
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7 * 25)
    weeks = [[start + timedelta(days=week * 7 + weekday) for weekday in range(7)] for week in range(26)]
    peak = max((daily.get(day, 0) for week in weeks for day in week), default=0)
    cells = []
    for column, week in enumerate(weeks):
        for row, day in enumerate(week):
            count = daily.get(day, 0)
            x, y = 22 + column * 25, 52 + row * 14
            cells.append(
                f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" '
                f'fill="{cell_color(count, peak)}" stroke="#14324A" stroke-width=".5">'
                f'<title>{day.isoformat()}: {count} contributions</title></rect>'
            )

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg width="1200" height="360" viewBox="0 0 1200 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">SIWOO GitHub live signal for {html.escape(login)}</title>
  <desc id="desc">{total} total contributions. Current streak {current} days. Longest streak {longest} days. Updated {updated}.</desc>
  <defs>
    <linearGradient id="signal-bg" x1="0" y1="0" x2="1200" y2="360" gradientUnits="userSpaceOnUse"><stop stop-color="#02060B"/><stop offset="1" stop-color="#07111B"/></linearGradient>
    <pattern id="signal-grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#0C2030" stroke-width="1"/></pattern>
  </defs>
  <rect width="1200" height="360" rx="22" fill="url(#signal-bg)"/>
  <rect width="1200" height="360" rx="22" fill="url(#signal-grid)" opacity=".6"/>
  <rect x=".75" y=".75" width="1198.5" height="358.5" rx="21.25" fill="none" stroke="#14324A" stroke-width="1.5"/>
  <g font-family="SFMono-Regular,Menlo,Consolas,monospace">
    <text x="42" y="44" fill="#8B949E" font-size="15">GITHUB_SIGNAL // CONTRIBUTION TELEMETRY</text>
    <circle cx="1030" cy="39" r="5" fill="#34C759"/><text x="1046" y="44" fill="#8B949E" font-size="13">STATUS: LIVE</text>
    <text x="42" y="76" fill="#00AAFF" font-size="13">USER: {html.escape(login)}</text>
    <text x="1158" y="334" text-anchor="end" fill="#8B949E" font-size="12">UPDATED: {updated}</text>
  </g>
  <g font-family="-apple-system,BlinkMacSystemFont,Arial,sans-serif">
    <g transform="translate(42 106)"><rect width="184" height="174" rx="15" fill="#050B12" stroke="#14324A"/><text x="20" y="33" fill="#00AAFF" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">TOTAL CONTRIBUTIONS</text><text x="20" y="95" fill="#F0F6FC" font-size="42" font-weight="700">{total:,}</text><path d="M20 124H164" stroke="#007AFF" stroke-width="2" opacity=".7"/><text x="20" y="151" fill="#8B949E" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">ALL TIME</text></g>
    <g transform="translate(244 106)"><rect width="184" height="174" rx="15" fill="#050B12" stroke="#14324A"/><text x="20" y="33" fill="#00AAFF" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">CURRENT STREAK</text><text x="20" y="95" fill="#F0F6FC" font-size="42" font-weight="700">{current}<tspan font-size="18" fill="#8B949E"> DAYS</tspan></text><path d="M20 124H164" stroke="#007AFF" stroke-width="2" opacity=".7"/><text x="20" y="151" fill="#8B949E" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">ACTIVE RUN</text></g>
    <g transform="translate(446 106)"><rect width="712" height="174" rx="15" fill="#050B12" stroke="#14324A"/><text x="22" y="33" fill="#00AAFF" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">CONTRIBUTION ACTIVITY // LAST 26 WEEKS</text>{''.join(cells)}<text x="22" y="151" fill="#8B949E" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">LOW</text><rect x="62" y="141" width="13" height="13" rx="3" fill="#14324A"/><rect x="81" y="141" width="13" height="13" rx="3" fill="#007AFF"/><rect x="100" y="141" width="13" height="13" rx="3" fill="#00AAFF"/><rect x="119" y="141" width="13" height="13" rx="3" fill="#34C759"/><text x="143" y="151" fill="#8B949E" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">HIGH</text></g>
    <g transform="translate(42 298)"><rect width="1116" height="38" rx="10" fill="#050B12" stroke="#007AFF"/><text x="20" y="25" fill="#00AAFF" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">LONGEST STREAK</text><text x="190" y="26" fill="#F0F6FC" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="16" font-weight="700">{longest} DAYS</text><text x="1094" y="25" text-anchor="end" fill="#34C759" font-family="SFMono-Regular,Menlo,Consolas,monospace" font-size="12">DATA SOURCE: GITHUB GRAPHQL API</text></g>
  </g>
</svg>'''


def main():
    login, total, daily = fetch_contributions()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(login, total, daily), encoding="utf-8")


if __name__ == "__main__":
    main()
