#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Convert newsletter Markdown (GitHub/Confluence friendly) into
Slack-friendly text (bold headings, bullets, <url|text> links, emojis).

Input env vars:
  MD     -> path to the .md file (source)
  SLACK  -> path to the _slack.txt file (destination)
"""

import os
import re
import sys

md_path = os.environ.get("MD")
slack_path = os.environ.get("SLACK")

if not md_path or not slack_path:
    print("[ERROR] MD and/or SLACK env vars not set", file=sys.stderr)
    sys.exit(1)

if not os.path.exists(md_path):
    print(f"[ERROR] Markdown file not found: {md_path}", file=sys.stderr)
    sys.exit(1)

with open(md_path, "r", encoding="utf-8") as f:
    md = f.read()

# Headings -> bold with emojis for known sections
HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

def add_emoji(title: str) -> str:
    t = title.strip().lower()
    if "ai in trade finance" in t:
        return f"📢 {title}"
    if "tip of the week" in t:
        return f"💡 {title}"
    if "internal spotlight" in t:
        return f"🔍 {title}"
    if "quick hits" in t:
        return f"⚡ {title}"
    if "mitimind" in t or "newsletter" in t:
        return f"🗞️ {title}"
    return title

def heading_to_bold(match: re.Match) -> str:
    title = match.group(2).strip()
    return f"*{add_emoji(title)}*"

md = HEADER_RE.sub(heading_to_bold, md)

# Bullets: "- " at start of line -> "• "
md = re.sub(r"(?m)^\s*-\s+", "• ", md)

# Links: [text](url) -> <url|text>
md = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"<\2|\1>", md)

with open(slack_path, "w", encoding="utf-8") as f:
    f.write(md)
    f.write("\n\n_Read the full issue in Confluence once published._")

print(f"[OK] Slack text written to {slack_path}")
