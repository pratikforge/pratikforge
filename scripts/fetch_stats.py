"""Fetch live public-safe GitHub GraphQL stats and 53-week contribution calendar."""

import json
import os
import re
import urllib.request
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "stats.json"

EXCLUDED_LANGS = {
    "HTML", "CSS", "SCSS", "Shell", "Batchfile",
    "PowerShell", "Dockerfile", "Makefile", "HCL",
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            weekday
          }
        }
      }
    }
    followers { totalCount }
    pullRequests(first: 1) { totalCount }
    issues(first: 1) { totalCount }
  }
}
"""


def fetch_stats(login: str, token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9-]+", login):
        raise ValueError(f"Invalid GitHub username: {login!r}")

    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-readme-sync",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if "errors" in payload:
        raise RuntimeError(f"GraphQL error: {payload['errors']}")

    user = payload["data"]["user"]
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]

    cur = longest = 0
    for d in days:
        if d["contributionCount"] > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    active_days = sum(1 for d in days if d["contributionCount"] > 0)

    monthly_map: OrderedDict[str, int] = OrderedDict()
    for d in days:
        ym = d["date"][:7]
        monthly_map[ym] = monthly_map.get(ym, 0) + d["contributionCount"]

    last_12 = list(monthly_map.items())[-12:]
    monthly = [
        {"ym": ym, "label": datetime.strptime(ym, "%Y-%m").strftime("%b"), "total": total}
        for ym, total in last_12
    ]

    lang_bytes: dict[str, int] = {}
    stars = 0
    for node in user["repositories"]["nodes"]:
        stars += node["stargazerCount"]
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            if name not in EXCLUDED_LANGS:
                lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

    total_code = sum(lang_bytes.values()) or 1
    ranked = sorted(lang_bytes.items(), key=lambda kv: -kv[1])
    top4 = [(k, v) for k, v in ranked[:4] if round(v * 100.0 / total_code, 1) >= 0.1]
    other_bytes = sum(v for _, v in ranked[len(top4):])
    languages = [{"name": k, "pct": round(v * 100.0 / total_code, 1)} for k, v in top4]
    if other_bytes > 0:
        rem = round(max(0.1, 100.0 - sum(x["pct"] for x in languages)), 1)
        languages.append({"name": "Other", "pct": rem})

    return {
        "login": login,
        "total_contributions": cal["totalContributions"],
        "total_commits": cc["totalCommitContributions"],
        "pull_requests": user["pullRequests"]["totalCount"],
        "issues": user["issues"]["totalCount"],
        "total_repos": user["repositories"]["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "active_days": active_days,
        "longest_streak": longest,
        "languages": languages,
        "weeks": [
            [{"date": d["date"], "count": d["contributionCount"], "weekday": d["weekday"]} for d in w["contributionDays"]]
            for w in weeks
        ],
        "monthly": monthly,
    }


def main() -> None:
    login = os.environ.get("GH_USERNAME", "pratikforge")
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GH_TOKEN environment variable is required")
    data = fetch_stats(login, token)
    OUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    langs_str = ", ".join(f"{x['name']} {x['pct']}%" for x in data["languages"])
    print(
        f"Wrote {OUT_PATH.name}: {data['total_contributions']} contribs, "
        f"{data['longest_streak']}d streak, {data['pull_requests']} PRs, "
        f"{data['total_repos']} public repos, {data['stars']} stars | {langs_str}"
    )


if __name__ == "__main__":
    main()
