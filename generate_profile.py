from __future__ import annotations

import calendar
import html
import os
from datetime import date, datetime
from pathlib import Path

import requests


GITHUB_USERNAME = "lostspaceship"
BIRTH_DATE = os.getenv("PROFILE_BIRTH_DATE") or "2004-12-08"
WEBSITE_URL = "https://www.ftn.one/"
OUTPUT_FILE = Path("README.md")
ASCII_ART_FILE = Path("ascii-art.txt")
PROFILE_IMAGES = {
    "dark": Path("dark_mode.svg"),
    "light": Path("light_mode.svg"),
}
SVG_WIDTH = 1000
SVG_HEIGHT = 496
SVG_PADDING = 24
ASCII_MAX_LINES = 21
ASCII_X = 24
INFO_X = 428
FIRST_LINE_Y = 36
LINE_HEIGHT = 20
INFO_WIDTH = 56

THEMES = {
    "dark": {
        "background": "#161b22",
        "text": "#c9d1d9",
        "key": "#ffa657",
        "value": "#a5d6ff",
        "muted": "#8b949e",
    },
    "light": {
        "background": "#f6f8fa",
        "text": "#24292f",
        "key": "#bf6700",
        "value": "#0969da",
        "muted": "#57606a",
    },
}


def access_token() -> str | None:
    return os.getenv("PROFILE_STATS_TOKEN") or os.getenv("GITHUB_TOKEN")


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lostspaceship-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_github_stats() -> dict[str, str]:
    # These preserve the current profile snapshot when GitHub's API is unavailable.
    stats = {
        "public_repos": "3",
        "private_repos": "n/a",
        "private_access": "no",
        "stars": "10",
        "commits": "4",
        "private_contributions": "76",
        "contributions": "81",
    }
    try:
        user_response = requests.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}",
            headers=github_headers(),
            timeout=20,
        )
        user_response.raise_for_status()
        user = user_response.json()
        stats["public_repos"] = f"{user['public_repos']:,}"

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

    profile_token = os.getenv("PROFILE_STATS_TOKEN")
    if profile_token:
        try:
            accessible_repos = []
            page = 1
            while True:
                repo_response = requests.get(
                    "https://api.github.com/user/repos",
                    params={
                        "affiliation": "owner",
                        "visibility": "all",
                        "per_page": 100,
                        "page": page,
                    },
                    headers=github_headers(),
                    timeout=20,
                )
                repo_response.raise_for_status()
                batch = repo_response.json()
                accessible_repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            stats["private_repos"] = f"{sum(repo['private'] for repo in accessible_repos):,}"
            stats["private_access"] = "yes"
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            print(f"Private repository statistics update skipped: {error}")

    token = access_token()
    if not token:
        return stats

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
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
        stats["private_contributions"] = (
            f"{contributions['restrictedContributionsCount']:,}"
        )
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
        return "birth date needed"
    try:
        born = datetime.strptime(BIRTH_DATE, "%Y-%m-%d").date()
    except ValueError:
        return "invalid birth date"

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


def profile_rows(stats: dict[str, str]) -> list[list[tuple[str, str]]]:
    def heading(title: str) -> list[tuple[str, str]]:
        rule_length = max(4, INFO_WIDTH - len(title) - 3)
        return [("text", f"- {title} "), ("muted", "-" * rule_length)]

    def row(key: str, value: str) -> list[tuple[str, str]]:
        prefix_length = len(key) + 3
        dot_count = max(2, INFO_WIDTH - prefix_length - len(value))
        return [
            ("muted", ". "),
            ("key", key),
            ("muted", ": " + "." * dot_count + " "),
            ("value", value),
        ]

    def paired_row(
        left_key: str, left_value: str, right_key: str, right_value: str
    ) -> list[tuple[str, str]]:
        return [
            ("muted", ". "),
            ("key", left_key),
            ("muted", ": "),
            ("value", left_value),
            ("muted", "  |  "),
            ("key", right_key),
            ("muted", ": "),
            ("value", right_value),
        ]

    stats_rows = [
        paired_row("Repos.Public", stats["public_repos"], "Stars.Public", stats["stars"]),
        row("Commits.Public.ThisYear", stats["commits"]),
        row("Contribs.Private.ThisYear", stats["private_contributions"]),
        row("Contribs.Total.ThisYear", stats["contributions"]),
    ]
    if stats["private_access"] == "yes":
        stats_rows.insert(1, row("Repos.Private", stats["private_repos"]))

    return [
        heading("FTN@CODE"),
        row("OS", "Windows 11, macOS, Linux"),
        row("Uptime", age_text()),
        row("Role", "Software Developer"),
        row("IDE", "VS Code, IntelliJ IDEA, PyCharm"),
        [],
        row("Languages.Programming", "Python, C++, Rust"),
        row("Languages.Web", "HTML, CSS"),
        row("Languages.Real", "Dutch, English, Albanian"),
        [],
        heading("Contact"),
        row("Handle", "ftn.code"),
        row("Email", "ftncode@gmail.com"),
        row("Discord", "999999999.6"),
        row("Website", "www.ftn.one"),
        [],
        heading("GitHub Stats"),
        *stats_rows,
        [("muted", "github.com/lostspaceship - updated daily")],
    ]


def ascii_lines() -> list[str]:
    lines = ASCII_ART_FILE.read_text(encoding="utf-8").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines[:ASCII_MAX_LINES]


def svg_line(x: int, y: int, segments: list[tuple[str, str]]) -> str:
    content = "".join(
        f'<tspan class="{style}">{html.escape(value)}</tspan>'
        for style, value in segments
    )
    return f'<text x="{x}" y="{y}">{content}</text>'


def render_svg(stats: dict[str, str], theme_name: str) -> str:
    theme = THEMES[theme_name]
    art = ascii_lines()
    rows = profile_rows(stats)
    art_svg = "\n".join(
        f'<text class="art" x="{ASCII_X}" y="{FIRST_LINE_Y + index * LINE_HEIGHT}">'
        f"{html.escape(line)}"
        "</text>"
        for index, line in enumerate(art)
    )
    info_svg = "\n".join(
        svg_line(INFO_X, FIRST_LINE_Y + index * LINE_HEIGHT, row)
        for index, row in enumerate(rows)
        if row
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" role="img" aria-labelledby="title description">
  <title id="title">FTN GitHub profile</title>
  <desc id="description">Terminal-style profile for the lostspaceship GitHub account.</desc>
  <style>
    .art, text {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 16px; white-space: pre; }}
    .art, .text {{ fill: {theme["text"]}; }}
    .key {{ fill: {theme["key"]}; }}
    .value {{ fill: {theme["value"]}; }}
    .muted {{ fill: {theme["muted"]}; }}
  </style>
  <rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" rx="12" fill="{theme["background"]}" />
  {art_svg}
  {info_svg}
</svg>
'''


def render_readme() -> str:
    image_base_url = (
        "https://raw.githubusercontent.com/lostspaceship/lostspaceship/main"
    )
    return f'''<!-- This README is generated by generate_profile.py. -->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="{image_base_url}/dark_mode.svg">
    <img alt="FTN's GitHub profile" src="{image_base_url}/light_mode.svg" width="100%">
  </picture>
</p>

<p align="center"><a href="{WEBSITE_URL}">{WEBSITE_URL}</a></p>
'''


def main() -> None:
    stats = fetch_github_stats()
    for theme_name, output_file in PROFILE_IMAGES.items():
        output_file.write_text(render_svg(stats, theme_name), encoding="utf-8")
    OUTPUT_FILE.write_text(render_readme(), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE} and profile SVGs for @{GITHUB_USERNAME}")


if __name__ == "__main__":
    main()
