from __future__ import annotations

import calendar
import html
import os
from datetime import date, datetime
from pathlib import Path

import requests


GITHUB_USERNAME = "lostspaceship"
BIRTH_DATE = os.getenv("BIRTH_DATE", "")  # Set to YYYY-12-21 after the year is confirmed.
OUTPUT_FILE = Path("profile.svg")
ASCII_ART_FILE = Path("ascii-art.txt")
INFO_X = 475


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lostspaceship-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_github_stats() -> dict[str, str]:
    stats = {
        "repos": "4",
        "stars": "10",
        "followers": "1",
        "commits": "—",
        "contributions": "—",
    }
    try:
        user_response = requests.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}",
            headers=github_headers(),
            timeout=20,
        )
        user_response.raise_for_status()
        user = user_response.json()
        stats["repos"] = f"{user['public_repos']:,}"
        stats["followers"] = f"{user['followers']:,}"

        repo_response = requests.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos",
            params={"per_page": 100, "type": "owner"},
            headers=github_headers(),
            timeout=20,
        )
        repo_response.raise_for_status()
        stats["stars"] = f"{sum(repo['stargazers_count'] for repo in repo_response.json()):,}"
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        print(f"REST statistics update skipped: {error}")

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return stats

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """
    try:
        graph_response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": GITHUB_USERNAME}},
            headers=github_headers(),
            timeout=20,
        )
        graph_response.raise_for_status()
        payload = graph_response.json()
        if payload.get("errors"):
            raise ValueError(payload["errors"])
        contributions = payload["data"]["user"]["contributionsCollection"]
        stats["commits"] = f"{contributions['totalCommitContributions']:,}"
        stats["contributions"] = (
            f"{contributions['contributionCalendar']['totalContributions']:,}"
        )
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        print(f"GraphQL statistics update skipped: {error}")

    return stats


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def age_text() -> str:
    if not BIRTH_DATE:
        return "21 December · birth year needed"
    try:
        born = datetime.strptime(BIRTH_DATE, "%Y-%m-%d").date()
    except ValueError:
        return "21 December · invalid birth year"

    today = date.today()
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    anniversary = add_months(born, years * 12)
    months = 0
    while add_months(anniversary, months + 1) <= today:
        months += 1
    month_mark = add_months(anniversary, months)
    days = (today - month_mark).days
    return f"{years} years, {months} months, {days} days"


def tspans_for_ascii() -> str:
    ascii_art = ASCII_ART_FILE.read_text(encoding="utf-8").strip("\r\n")
    lines = []
    for index, line in enumerate(ascii_art.splitlines()):
        y = 31 + index * 20
        lines.append(f'<tspan x="14" y="{y:g}">{html.escape(line)}</tspan>')
    return "\n    ".join(lines)


def row(y: int, key: str, value: str) -> str:
    return (
        f'<tspan x="{INFO_X}" y="{y}" class="muted">. </tspan>'
        f'<tspan class="key">{html.escape(key)}</tspan>'
        f'<tspan class="muted">: </tspan>'
        f'<tspan class="value">{html.escape(value)}</tspan>'
    )


def rule(y: int, title: str) -> str:
    line = "─" * max(3, 48 - len(title))
    return f'<tspan x="{INFO_X}" y="{y}" class="heading">- {html.escape(title)} {line}</tspan>'


def render_svg(stats: dict[str, str]) -> str:
    content = [
        rule(35, "FTN@CODE"),
        row(62, "OS", "Windows 11, macOS, Linux"),
        row(86, "Uptime", age_text()),
        row(110, "Role", "Software Developer"),
        row(134, "IDE", "VS Code, IntelliJ IDEA, PyCharm"),
        row(174, "Languages.Programming", "Python, C++, Rust"),
        row(198, "Languages.Web", "HTML, CSS"),
        row(222, "Languages.Real", "Dutch, English, Albanian"),
        rule(270, "Contact"),
        row(297, "Handle", "ftn.code"),
        row(321, "Email", "ftncode@gmail.com"),
        row(345, "Discord", "999999999.6"),
        row(369, "Website", "ftn.fc.school"),
        rule(417, "GitHub Stats"),
        row(444, "Repos", stats["repos"]),
        row(468, "Stars", stats["stars"]),
        row(492, "Commits.ThisYear", stats["commits"]),
        row(516, "Contributions.ThisYear", stats["contributions"]),
        row(540, "Followers", stats["followers"]),
        f'<tspan x="{INFO_X}" y="584" class="foot">github.com/lostspaceship · updated daily</tspan>',
    ]
    info = "\n    ".join(content)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="610" viewBox="0 0 1000 610" role="img" aria-labelledby="title desc">
  <title id="title">FTN GitHub profile</title>
  <desc id="desc">Red and black terminal-style profile for lostspaceship</desc>
  <style>
    text {{ white-space: pre; font-family: Consolas, "Liberation Mono", monospace; }}
    .ascii {{ fill: #ff2d2d; font-size: 16px; }}
    .info {{ font-size: 15px; }}
    .heading {{ fill: #ff3b3b; font-weight: 700; }}
    .key {{ fill: #ff3b3b; font-weight: 700; }}
    .value {{ fill: #f4f4f4; }}
    .muted {{ fill: #707070; }}
    .foot {{ fill: #666; font-size: 12px; }}
  </style>
  <rect x="2" y="2" width="996" height="606" rx="18" fill="#050505" stroke="#5f1010" stroke-width="2"/>
  <line x1="455" y1="24" x2="455" y2="586" stroke="#361010"/>
  <text class="ascii">
    {tspans_for_ascii()}
  </text>
  <text class="info">
    {info}
  </text>
</svg>
'''


def main() -> None:
    stats = fetch_github_stats()
    OUTPUT_FILE.write_text(render_svg(stats), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE} for @{GITHUB_USERNAME}")


if __name__ == "__main__":
    main()
