"""Generate the public chart from GitHub's repository language metadata."""

import argparse
from collections import Counter
from html import escape
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "languages.svg"


def github(path, token):
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise SystemExit(f"GitHub API request failed (HTTP {error.code}).") from None


def collect(token, owner):
    if github("/user", token)["login"].casefold() != owner.casefold():
        raise SystemExit("The token must belong to the profile owner.")

    totals = Counter()
    page = 1
    while True:
        query = urlencode({
            "affiliation": "owner", "visibility": "all", "per_page": 100,
            "page": page, "sort": "full_name",
        })
        repositories = github(f"/user/repos?{query}", token)
        for repo in repositories:
            languages = github(f"/repos/{repo['full_name']}/languages", token)
            total_bytes = sum(languages.values())
            if total_bytes:
                largest = max(languages.values())
                totals.update(
                    name for name, size in languages.items()
                    if size == largest or size * 100 >= total_bytes
                )
        if len(repositories) < 100:
            break
        page += 1
    return totals


def render(totals, empty_message):
    entries = sorted(totals.items(), key=lambda item: (-item[1], item[0].casefold()))
    height = max(56, 24 * len(entries) + 16)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" '
        f'viewBox="0 0 360 {height}" role="img" aria-labelledby="title">',
        '<title id="title">Languages by Project</title>',
        '<g font-family="system-ui, sans-serif" font-size="13">',
    ]
    if entries:
        description = ", ".join(f"{name}: {count}" for name, count in entries)
        parts.append(f'<desc>Project counts: {escape(description)}</desc>')
        largest = entries[0][1]
        for index, (name, count) in enumerate(entries):
            y = 20 + index * 24
            label = name if len(name) <= 18 else name[:17] + "…"
            bar_width = 154 * count / largest
            parts.extend([
                f'<text x="10" y="{y + 5}" fill="#68788c">{escape(label)}</text>',
                f'<rect x="166" y="{y - 4}" width="154" height="8" rx="4" fill="#8291a8" opacity=".19"/>',
                f'<rect x="166" y="{y - 4}" width="{bar_width:.2f}" height="8" rx="4" fill="#668ad1"/>',
                f'<text x="350" y="{y + 5}" text-anchor="end" fill="#68788c">{count}</text>',
            ])
    else:
        parts.append(f'<text x="10" y="32" fill="#68788c">{escape(empty_message)}</text>')
    parts.extend(["</g>", "</svg>"])
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--placeholder", action="store_true")
    args = parser.parse_args()
    if args.placeholder:
        chart = render({}, "Awaiting first update")
    else:
        token = os.environ.get("PROFILE_LANGUAGES_TOKEN")
        owner = os.environ.get("PROFILE_OWNER")
        if not token or not owner:
            parser.error("Set PROFILE_LANGUAGES_TOKEN and PROFILE_OWNER.")
        chart = render(collect(token, owner), "No language data")
    OUTPUT.write_text(chart, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
