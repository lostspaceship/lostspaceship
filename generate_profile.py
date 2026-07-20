from __future__ import annotations

import calendar
import os
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Optional

import requests


GITHUB_USERNAME = "lostspaceship"
BIRTH_DATE = os.getenv("PROFILE_BIRTH_DATE") or "2004-12-08"
WEBSITE_URL = "https://www.ftn.one/"

OUTPUT_FILE = Path("README.md")
DARK_SVG_FILE = Path("dark_mode.svg")
LIGHT_SVG_FILE = Path("light_mode.svg")
ASCII_ART_FILE = Path("ascii-art.txt")

PROFILE_REPOSITORY = f"{GITHUB_USERNAME}/{GITHUB_USERNAME}"
PROFILE_URL = f"https://github.com/{PROFILE_REPOSITORY}"
RAW_ASSET_URL = f"https://raw.githubusercontent.com/{PROFILE_REPOSITORY}/main"

SVG_WIDTH = 985
FONT_SIZE = 16
LINE_HEIGHT = 20
START_Y = 30
BOTTOM_PADDING = 25
ART_X = 15
ASCII_MAX_LINES = 21
INFO_X = 430
INFO_WIDTH = 56

THEMES = {
    "dark": {
        "background": "#161b22",
        "text": "#c9d1d9",
        "key": "#ffa657",
        "value": "#a5d6ff",
        "muted": "#616e7f",
    },
    "light": {
        "background": "#f6f8fa",
        "text": "#24292f",
        "key": "#bf6700",
        "value": "#0969da",
        "muted": "#57606a",
    },
}

TextChunk = tuple[Optional[str], str]
TextRow = list[TextChunk]


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


def dot_count(prefix: str, value: str, width: int = INFO_WIDTH) -> int:
    return max(2, width - len(prefix) - len(value) - 2)


def key_chunks(key: str) -> TextRow:
    chunks: TextRow = []
    parts = key.split(".")
    for index, part in enumerate(parts):
        chunks.append(("key", part))
        if index < len(parts) - 1:
            chunks.append((None, "."))
    return chunks


def info_row(key: str, value: str, width: int = INFO_WIDTH) -> TextRow:
    prefix = f". {key}:"
    dots = "." * dot_count(prefix, value, width)
    return [("muted", ". "), *key_chunks(key), (None, ":"), ("muted", f" {dots} "), ("value", value)]


def section_row(title: str, width: int = INFO_WIDTH) -> TextRow:
    prefix = f"- {title} "
    rule = "-" * max(3, width - len(prefix))
    return [(None, prefix), ("muted", rule)]


def blank_row() -> TextRow:
    return [("muted", ". ")]


def ascii_lines() -> list[str]:
    lines = ASCII_ART_FILE.read_text(encoding="utf-8").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return [line.rstrip() for line in lines[:ASCII_MAX_LINES]]


def stats_overview_row(stats: dict[str, str]) -> TextRow:
    private_label = "Private" if stats["private_access"] == "yes" else "Private"
    private_value = stats["private_repos"]
    return [
        ("muted", ". "),
        ("key", "Repos"),
        (None, ":"),
        ("muted", " .... "),
        ("value", stats["public_repos"]),
        (None, " {"),
        ("key", private_label),
        (None, ": "),
        ("value", private_value),
        (None, "} | "),
        ("key", "Stars"),
        (None, ":"),
        ("muted", " ....... "),
        ("value", stats["stars"]),
    ]


def stats_activity_row(stats: dict[str, str]) -> TextRow:
    return [
        ("muted", ". "),
        ("key", "Commits"),
        (None, ":"),
        ("muted", " ......... "),
        ("value", stats["commits"]),
        (None, " | "),
        ("key", "Private Contribs"),
        (None, ": "),
        ("value", stats["private_contributions"]),
    ]


def profile_rows(stats: dict[str, str]) -> list[TextRow]:
    return [
        section_row("FTN@CODE"),
        info_row("OS", "Windows 11, macOS, Linux"),
        info_row("Uptime", age_text()),
        info_row("Role", "Software Developer"),
        info_row("IDE", "VS Code, IntelliJ IDEA, PyCharm"),
        blank_row(),
        info_row("Languages.Programming", "Python, C++, Rust"),
        info_row("Languages.Web", "HTML, CSS"),
        info_row("Languages.Real", "Dutch, English, Albanian"),
        blank_row(),
        section_row("Contact"),
        info_row("Handle", "ftn.code"),
        info_row("Email", "ftncode@gmail.com"),
        info_row("Discord", "999999999.6"),
        info_row("Website", "www.ftn.one"),
        blank_row(),
        section_row("GitHub Stats"),
        stats_overview_row(stats),
        stats_activity_row(stats),
        info_row("Total Contributions", stats["contributions"]),
        [(None, "github.com/lostspaceship"), ("muted", " - updated daily")],
    ]


def svg_height(line_count: int) -> int:
    return START_Y + (line_count - 1) * LINE_HEIGHT + BOTTOM_PADDING


def svg_tspan(chunk: TextChunk, x: int | None = None, y: int | None = None) -> str:
    class_name, text = chunk
    attrs = []
    if x is not None:
        attrs.append(f'x="{x}"')
    if y is not None:
        attrs.append(f'y="{y}"')
    if class_name:
        attrs.append(f'class="{class_name}"')
    attr_text = " " + " ".join(attrs) if attrs else ""
    return f"<tspan{attr_text}>{escape(text)}</tspan>"


def render_text_rows(rows: list[TextRow], x: int, fill: str) -> str:
    output = [f'<text x="{x}" y="{START_Y}" fill="{fill}">']
    for index, row in enumerate(rows):
        y = START_Y + index * LINE_HEIGHT
        first, *rest = row
        output.append(svg_tspan(first, x=x, y=y) + "".join(svg_tspan(chunk) for chunk in rest))
    output.append("</text>")
    return "\n".join(output)


def render_ascii_rows(rows: list[str], x: int, fill: str) -> str:
    output = [f'<text x="{x}" y="{START_Y}" fill="{fill}" class="ascii">']
    for index, row in enumerate(rows):
        y = START_Y + index * LINE_HEIGHT
        output.append(f'<tspan x="{x}" y="{y}">{escape(row)}</tspan>')
    output.append("</text>")
    return "\n".join(output)


def render_svg(theme_name: str, stats: dict[str, str]) -> str:
    theme = THEMES[theme_name]
    art = ascii_lines()
    info = profile_rows(stats)
    line_count = max(len(art), len(info))
    art.extend([""] * (line_count - len(art)))
    height = svg_height(line_count)

    return "\n".join(
        [
            "<?xml version='1.0' encoding='UTF-8'?>",
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'font-family="ConsolasFallback, Consolas, monospace" '
                f'width="{SVG_WIDTH}px" height="{height}px" font-size="{FONT_SIZE}px">'
            ),
            "<style>",
            "@font-face {",
            "src: local('Consolas'), local('Consolas Bold');",
            "font-family: 'ConsolasFallback';",
            "font-display: swap;",
            "-webkit-size-adjust: 109%;",
            "size-adjust: 109%;",
            "}",
            f".key {{fill: {theme['key']};}}",
            f".value {{fill: {theme['value']};}}",
            f".muted {{fill: {theme['muted']};}}",
            "text, tspan {white-space: pre;}",
            "</style>",
            (
                f'<rect width="{SVG_WIDTH}px" height="{height}px" '
                f'fill="{theme["background"]}" rx="15"/>'
            ),
            render_ascii_rows(art, ART_X, theme["text"]),
            render_text_rows(info, INFO_X, theme["text"]),
            "</svg>",
        ]
    )


def render_readme() -> str:
    dark_url = f"{RAW_ASSET_URL}/{DARK_SVG_FILE.name}"
    light_url = f"{RAW_ASSET_URL}/{LIGHT_SVG_FILE.name}"
    return (
        "<!-- This README is generated by generate_profile.py. -->\n\n"
        f'<a href="{PROFILE_URL}">\n'
        "  <picture>\n"
        f'    <source media="(prefers-color-scheme: dark)" srcset="{dark_url}">\n'
        f'    <img alt="FTN GitHub profile README" src="{light_url}">\n'
        "  </picture>\n"
        "</a>\n"
    )


def main() -> None:
    stats = fetch_github_stats()
    DARK_SVG_FILE.write_text(render_svg("dark", stats), encoding="utf-8")
    LIGHT_SVG_FILE.write_text(render_svg("light", stats), encoding="utf-8")
    OUTPUT_FILE.write_text(render_readme(), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}, {DARK_SVG_FILE}, and {LIGHT_SVG_FILE} for @{GITHUB_USERNAME}")


if __name__ == "__main__":
    main()
