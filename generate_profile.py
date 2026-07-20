from __future__ import annotations

import calendar
import os
from datetime import date, datetime
from pathlib import Path

import requests


GITHUB_USERNAME = "lostspaceship"
BIRTH_DATE = os.getenv("PROFILE_BIRTH_DATE") or "2004-12-08"
WEBSITE_URL = "https://www.ftn.one/"
OUTPUT_FILE = Path("README.md")
ASCII_ART_FILE = Path("ascii-art.txt")
ASCII_MAX_LINES = 22
INFO_WIDTH = 50


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


def info_row(key: str, value: str, width: int = INFO_WIDTH) -> str:
    prefix = f". {key}:"
    dot_count = max(2, width - len(prefix) - len(value) - 2)
    return f"{prefix} {'.' * dot_count} {value}"


def section(title: str, width: int = INFO_WIDTH) -> str:
    prefix = f"- {title} "
    return prefix + "-" * max(3, width - len(prefix))


def ascii_lines() -> list[str]:
    lines = ASCII_ART_FILE.read_text(encoding="utf-8").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines[:ASCII_MAX_LINES]


def profile_rows(stats: dict[str, str]) -> list[str]:
    stats_rows = [
        f". Repos.Public: {stats['public_repos']}  |  Stars.Public: {stats['stars']}",
        info_row("Commits.Public.ThisYear", stats["commits"]),
        info_row("Contribs.Private.ThisYear", stats["private_contributions"]),
        info_row("Contribs.Total.ThisYear", stats["contributions"]),
    ]
    if stats["private_access"] == "yes":
        stats_rows.insert(1, info_row("Repos.Private", stats["private_repos"]))

    return [
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
        info_row("Website", "www.ftn.one"),
        "",
        section("GitHub Stats"),
        *stats_rows,
        "github.com/lostspaceship - updated daily",
    ]


def render_readme(stats: dict[str, str]) -> str:
    art = ascii_lines()
    info = profile_rows(stats)
    art_width = max(len(line.rstrip()) for line in art)
    line_count = max(len(art), len(info))
    art.extend([""] * (line_count - len(art)))
    info.extend([""] * (line_count - len(info)))
    profile = "\n".join(
        f"- {left.rstrip():<{art_width}} | {right}".rstrip()
        for left, right in zip(art, info)
    )
    return (
        "<!-- This README is generated by generate_profile.py. -->\n\n"
        "```diff\n"
        f"{profile}\n"
        "```\n\n"
        f'<p align="center"><a href="{WEBSITE_URL}">{WEBSITE_URL}</a></p>\n'
    )


def main() -> None:
    OUTPUT_FILE.write_text(render_readme(fetch_github_stats()), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE} for @{GITHUB_USERNAME}")


if __name__ == "__main__":
    main()
