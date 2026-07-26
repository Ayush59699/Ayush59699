"""
Computes a 'Most Used Languages' card from only the user's most recently
pushed non-JavaScript-primary repos (default: last 15), and excludes
legacy/noise languages (html, css, typescript) from the aggregate.

Run inside GitHub Actions with GH_TOKEN set to a PAT (repo + read:user scopes).
Writes profile/top-langs.svg, styled to match the sci-fi theme.
"""

import os
import requests

TOKEN = os.environ["GH_TOKEN"]
USERNAME = "Ayush59699"
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}
EXCLUDE_LANGS = {"html", "css", "typescript"}
EXCLUDE_PRIMARY_LANGS = {"javascript"}  # skip repos whose PRIMARY language is JS
MAX_REPOS = 15


def get_repos():
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"sort": "pushed", "direction": "desc", "per_page": 100, "page": page},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if len(batch) < 100:
            break
    return repos


def pick_repos(repos):
    picked = []
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        lang = (repo.get("language") or "").lower()
        if lang in EXCLUDE_PRIMARY_LANGS:
            continue
        picked.append(repo)
        if len(picked) >= MAX_REPOS:
            break
    return picked


def get_languages(repo_name):
    r = requests.get(
        f"https://api.github.com/repos/{USERNAME}/{repo_name}/languages",
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    repos = get_repos()
    picked = pick_repos(repos)

    totals = {}
    for repo in picked:
        langs = get_languages(repo["name"])
        for lang, count in langs.items():
            if lang.lower() in EXCLUDE_LANGS:
                continue
            totals[lang] = totals.get(lang, 0) + count

    total_bytes = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:6]

    colors = ["#ff00ff", "#00f0ff", "#8be9fd", "#ff79c6", "#bd93f9", "#50fa7b"]

    rows = ""
    y = 66
    for i, (lang, count) in enumerate(ranked):
        pct = count / total_bytes * 100
        bar_width = max(pct * 2.9, 4)
        color = colors[i % len(colors)]
        rows += f'''
        <text x="20" y="{y}" fill="#8be9fd" font-family="Fira Code, monospace" font-size="13">{lang}</text>
        <text x="330" y="{y}" fill="#8be9fd" font-family="Fira Code, monospace" font-size="12" text-anchor="end">{pct:.1f}%</text>
        <rect x="20" y="{y + 8}" width="310" height="6" rx="3" fill="#1e1b3a"/>
        <rect x="20" y="{y + 8}" width="{bar_width:.1f}" height="6" rx="3" fill="{color}"/>
        '''
        y += 34

    height = y + 12
    svg = f'''<svg width="370" height="{height}" viewBox="0 0 370 {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="370" height="{height}" rx="10" fill="#0f0c29"/>
  <text x="20" y="30" fill="#00f0ff" font-family="Fira Code, monospace" font-size="15" font-weight="bold">Most Used Languages</text>
  <text x="20" y="48" fill="#6b6f8f" font-family="Fira Code, monospace" font-size="10">Last {len(picked)} active repos</text>
  {rows}
</svg>'''

    os.makedirs("profile", exist_ok=True)
    with open("profile/top-langs.svg", "w") as f:
        f.write(svg)

    print(f"Wrote profile/top-langs.svg from {len(picked)} repos -> {len(ranked)} languages shown")


if __name__ == "__main__":
    main()
