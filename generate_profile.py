from __future__ import annotations

import calendar
import os
from datetime import date, datetime
from pathlib import Path

import requests


GITHUB_USERNAME = "lostspaceship"
BIRTH_DATE = os.getenv("BIRTH_DATE", "")  # Set to YYYY-12-21 after the year is confirmed.
OUTPUT_FILE = Path("README.md")
ASCII_ART_FILE = Path("ascii-art.txt")


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


def info_row(key: str, value: str, width: int = 57) -> str:
    prefix = f". {key}:"
    dot_count = max(1, width - len(prefix) - len(value) - 2)
    return f"{prefix} {'.' * dot_count} {value}"


def section(title: str, width: int = 57) -> str:
    prefix = f"- {title} "
    return prefix + "-" * max(3, width - len(prefix))


def render_readme(stats: dict[str, str]) -> str:
    ascii_lines = ASCII_ART_FILE.read_text(encoding="utf-8").strip("\r\n").splitlines()
    info_lines = [
        section("FTN@CODE"),
        info_row("OS", "Windows 11, macOS, Linux"),
        info_row("Uptime", age_text()),
        info_row("Role", "Software Developer"),
        info_row("IDE", "VS Code, IntelliJ IDEA, PyCharm"),
        "",
        info_row("Languages.Programming", "Python, C++, Rust"),
        info_row("Languages.Web", "HTML, CSS"),
        info_row("Languages.Real", "Dutch, English, Albanian"),
        "",
        section("Contact"),
        info_row("Handle", "ftn.code"),
        info_row("Email", "ftncode@gmail.com"),
        info_row("Discord", "999999999.6"),
        info_row("Website", "https://ftn.fc.school"),
        "",
        section("GitHub Stats"),
        info_row("Repos", stats["repos"]),
        info_row("Stars", stats["stars"]),
        info_row("Commits.ThisYear", stats["commits"]),
        info_row("Contributions.ThisYear", stats["contributions"]),
        info_row("Followers", stats["followers"]),
        "",
        "github.com/lostspaceship - updated daily",
    ]

    line_count = max(len(ascii_lines), len(info_lines))
    ascii_lines.extend([""] * (line_count - len(ascii_lines)))
    info_lines.extend([""] * (line_count - len(info_lines)))
    profile = "\n".join(
        f"{left.rstrip():<40} | {right}".rstrip()
        for left, right in zip(ascii_lines, info_lines)
    )
    return (
        "<!-- This README is generated by generate_profile.py. -->\n\n"
        "```text\n"
        f"{profile}\n"
        "```\n"
    )


def main() -> None:
    stats = fetch_github_stats()
    OUTPUT_FILE.write_text(render_readme(stats), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE} for @{GITHUB_USERNAME}")


if __name__ == "__main__":
    main()
