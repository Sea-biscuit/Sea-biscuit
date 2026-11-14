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
COLORS = ("#55c4f3", "#b19cff", "#57d8a5", "#ffc66d", "#fa92b9", "#a6bece", "#748aa5")


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
            totals.update(github(f"/repos/{repo['full_name']}/languages", token))
        if len(repositories) < 100:
            break
        page += 1
    return totals


def render(totals, empty_message):
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    entries = ranked[:6]
    if len(ranked) > 6:
        entries.append(("其他", sum(size for _, size in ranked[6:])))
    total = sum(totals.values())
    width, height = 600, 300
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
        '<title id="title">Language</title>',
        '<rect width="600" height="300" rx="20" fill="#111b2b"/>',
        '<circle cx="146" cy="150" r="86" fill="none" stroke="#29384e" stroke-width="24"/>',
        '<g font-family="system-ui, sans-serif" fill="#eaf1fa">',
    ]
    if total:
        parts.append('<desc>' + escape("，".join(
            f"{name} {size / total:.1%}" for name, size in entries
        )) + '</desc>')
        parts.append('<text x="146" y="156" text-anchor="middle" font-size="16">代码字节数</text>')
        offset = 0
        for index, (name, size) in enumerate(entries):
            color = COLORS[index]
            share = 100 * size / total
            y = 150 + (index - (len(entries) - 1) / 2) * 32
            label = name if len(name) <= 24 else name[:23] + "…"
            parts.extend([
                f'<circle cx="146" cy="150" r="86" fill="none" stroke="{color}" stroke-width="24" '
                f'pathLength="100" stroke-dasharray="{share:.9f} 100" stroke-dashoffset="{-offset:.9f}" '
                'transform="rotate(-90 146 150)"/>',
                f'<circle cx="288" cy="{y:.0f}" r="5" fill="{color}"/>',
                f'<text x="305" y="{y + 5:.0f}" font-size="16">{escape(label)}</text>',
                f'<text x="558" y="{y + 5:.0f}" text-anchor="end" font-size="16">{share:.1f}%</text>',
            ])
            offset += share
    else:
        parts.append(f'<text x="280" y="156" font-size="18">{escape(empty_message)}</text>')
    parts.extend(["</g>", "</svg>"])
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--placeholder", action="store_true")
    args = parser.parse_args()
    if args.placeholder:
        chart = render({}, "Waiting")
    else:
        token = os.environ.get("PROFILE_LANGUAGES_TOKEN")
        owner = os.environ.get("PROFILE_OWNER")
        if not token or not owner:
            parser.error("Set PROFILE_LANGUAGES_TOKEN and PROFILE_OWNER.")
        chart = render(collect(token, owner), "暂无可统计的语言")
    OUTPUT.write_text(chart, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
