#!/usr/bin/env python3
"""Génère profile/top-languages.svg à partir de tes dépôts GitHub, privés compris.

Variables d'environnement :
  GH_TOKEN  jeton GitHub (lecture seule) ; obligatoire
  EXCLUDE   langages à ignorer, séparés par des virgules (défaut : HTML,CSS,SCSS)
  TOP_N     nombre de langages affichés (défaut : 6)
  OUTPUT    chemin du fichier SVG (défaut : profile/top-languages.svg)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com"

COLORS = {
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "Kotlin": "#a97bff",
    "PHP": "#4f5d95",
    "Shell": "#89e051",
    "Python": "#3572a5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "CMake": "#da3434",
    "Makefile": "#427819",
}
DEFAULT_COLOR = "#8b949e"


def get(url, token):
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "top-languages-script",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def owned_repos(token):
    page = 1
    while True:
        url = (
            f"{API}/user/repos?affiliation=owner&visibility=all"
            f"&per_page=100&page={page}"
        )
        batch = get(url, token)
        if not batch:
            return
        for repo in batch:
            if not repo.get("fork"):
                yield repo
        page += 1


def collect(token, excluded):
    totals = {}
    for repo in owned_repos(token):
        try:
            languages = get(repo["languages_url"], token)
        except urllib.error.HTTPError as error:
            print(f"Ignoré {repo['full_name']} : HTTP {error.code}", file=sys.stderr)
            continue
        for name, size in languages.items():
            if name in excluded:
                continue
            totals[name] = totals.get(name, 0) + size
    return totals


def render(totals, top_n):
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:top_n]
    grand_total = sum(size for _, size in ranked) or 1
    row_height = 30
    width = 420
    height = 24 + row_height * max(len(ranked), 1)
    bar_x, bar_max = 130, 220
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Langages les plus utilisés">',
        "<style>"
        ".t{font:13px sans-serif;fill:#24292f}"
        ".b{fill:#d0d7de}"
        "@media (prefers-color-scheme: dark){.t{fill:#e6edf3}.b{fill:#30363d}}"
        "</style>",
    ]
    for index, (name, size) in enumerate(ranked):
        y = 16 + index * row_height
        percent = 100 * size / grand_total
        fill = COLORS.get(name, DEFAULT_COLOR)
        bar_width = max(2, bar_max * percent / 100)
        lines.append(f'<text class="t" x="12" y="{y + 12}">{escape(name)}</text>')
        lines.append(
            f'<rect class="b" x="{bar_x}" y="{y + 2}" width="{bar_max}" height="12" rx="6"/>'
        )
        lines.append(
            f'<rect x="{bar_x}" y="{y + 2}" width="{bar_width:.1f}" height="12" rx="6" fill="{fill}"/>'
        )
        lines.append(
            f'<text class="t" x="{bar_x + bar_max + 10}" y="{y + 12}">{percent:.1f} %</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN manquant")
    excluded = {
        name.strip()
        for name in os.environ.get("EXCLUDE", "HTML,CSS,SCSS").split(",")
        if name.strip()
    }
    top_n = int(os.environ.get("TOP_N", "6"))
    output = os.environ.get("OUTPUT", "profile/top-languages.svg")
    totals = collect(token, excluded)
    if not totals:
        sys.exit("Aucun langage trouvé : vérifie les droits du jeton")
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(render(totals, top_n))
    print(f"{output} écrit ({len(totals)} langages)")


if __name__ == "__main__":
    main()
