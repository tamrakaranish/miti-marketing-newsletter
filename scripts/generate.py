#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a draft AI newsletter (Markdown + Slack text).

Outputs:
  newsletter/<YYYY-MM-DD>.md
  newsletter/<YYYY-MM-DD>_slack.txt

Deps: feedparser, pyyaml, requests
Env:  OPENAI_API_KEY   (required)
"""

import os
import re
import json
import hashlib
import datetime as dt
from pathlib import Path
from textwrap import dedent

import feedparser          # pip install feedparser
import yaml                # pip install pyyaml
import requests            # pip install requests

# ----------------------------
# Config
# ----------------------------
ROOT = Path(__file__).resolve().parent.parent
SOURCES_YML = ROOT / "sources.yml"
OUTDIR = ROOT / "newsletter"
DATE = dt.date.today().isoformat()
OUT_MD = OUTDIR / f"{DATE}.md"
OUT_SLACK = OUTDIR / f"{DATE}_slack.txt"

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"   # keep aligned with your org policy

MAX_WORDS = 400
REQUIRED_MIN_LINKS = 3

# ----------------------------
# Helpers
# ----------------------------
def die(msg: str, code: int = 1):
    print(f"[ERROR] {msg}")
    raise SystemExit(code)

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def sha_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
    return h.hexdigest()[:16]

def load_sources(yml_path: Path):
    if not yml_path.exists():
        die(f"Missing sources.yml at {yml_path}.")
    with yml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    feeds = data.get("feeds") or []
    if not feeds:
        die("sources.yml has no 'feeds' entries.")
    return feeds

def fetch_items(feeds):
    items = []
    for feed in feeds:
        url = feed.get("url")
        name = feed.get("name") or url
        if not url:
            continue
        parsed = feedparser.parse(url)
        for e in parsed.entries:
            items.append({
                "source": name,
                "title": clean(getattr(e, "title", "")),
                "link": getattr(e, "link", "") or "",
                "summary": clean(getattr(e, "summary", "") or getattr(e, "description", "")),
                "published": getattr(e, "published", "") or ""
            })
    # De-duplicate by (title, link)
    seen, unique = set(), []
    for it in items:
        k = sha_key(it["title"], it["link"])
        if k in seen:
            continue
        seen.add(k)
        unique.append(it)
    return unique

def rank_items(items, limit=12):
    KEYS = ("ai", "model", "fintech", "trade", "compliance", "regulation", "customer", "b2b", "saas")
    scored = []
    for it in items:
        text = (it["title"] + " " + it["summary"]).lower()
        score = sum(k in text for k in KEYS)
        if it["link"]:
            score += 1
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:limit]]

def require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it in GitHub → Repo → Settings → Secrets → Actions.")
    return api_key

def summarize_with_openai(selected_items):
    api_key = require_api_key()

    system_msg = (
        "You produce a short internal AI newsletter for a trade-finance SaaS company. "
        "Be factual. Include source links next to claims. Avoid speculation and personal data."
    )
    user_payload = {
        "date": DATE,
        "instructions": dedent("""
            Write under 350 words with sections:
            1) AI in Trade Finance (1 item) + 'What this means for us'
            2) Tip of the Week
            3) Internal Spotlight (if none provided, suggest a small, safe internal experiment)
            4) Quick Hits (3 bullets)
            5) CTA for pilots/polls

            Rules:
            - Include the source link next to each claim (e.g., [Source](URL)).
            - If you are uncertain about a claim, exclude it or mark it clearly.
            - No confidential info. No personal data.
        """).strip(),
        "items": selected_items
    }

    body = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(body), timeout=60)
    if resp.status_code >= 300:
        die(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        die(f"Unexpected OpenAI response shape: {json.dumps(data)[:800]}")
    return content.strip()

def enforce_quality(md_text: str):
    words = re.findall(r"\b\w+\b", md_text)
    if len(words) > MAX_WORDS:
        die(f"Draft too long ({len(words)} words). Keep under {MAX_WORDS} words.")
    links = re.findall(r"https?://\S+", md_text)
    if len(links) < REQUIRED_MIN_LINKS:
        die(f"Draft contains too few links ({len(links)}). Require at least {REQUIRED_MIN_LINKS} source URLs.")
    for h in ("AI in Trade Finance", "Tip of the Week", "Quick Hits"):
        if h.lower() not in md_text.lower():
            die(f"Draft missing required section heading: '{h}'.")

# ---------- Slack formatting ----------
LINK_MD = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
HEADER_MD = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_MD = re.compile(r"^\s*-\s+")

def add_emoji_for_heading(title: str) -> str:
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

def convert_md_to_slack(markdown: str) -> str:
    lines = markdown.splitlines()
    out = []
    for ln in lines:
        m = HEADER_MD.match(ln)
        if m:
            title = m.group(2).strip()
            title = add_emoji_for_heading(title)
            out.append(f"*{title}*")
            continue
        if BULLET_MD.match(ln):
            ln = BULLET_MD.sub("• ", ln)
        ln = LINK_MD.sub(r"<\2|\1>", ln)  # [text](url) -> <url|text>
        out.append(ln)
    return "\n".join(out)

# ---------- Write outputs ----------
def write_outputs(md_body: str):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    header = f"# MitiMind – {DATE}\n\n"
    md_full = header + md_body + "\n\n— Auto‑draft by AI agent, please review before publishing.\n"
    # Markdown for PR/Confluence
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write(md_full)
    print(f"[OK] Markdown written to {OUT_MD}")
    # Slack-friendly text
    slack_text = convert_md_to_slack(md_full)
    with OUT_SLACK.open("w", encoding="utf-8") as f:
        f.write(slack_text)
        f.write("\n\n_Read the full issue in Confluence once published._")
    print(f"[OK] Slack text written to {OUT_SLACK}")

# ----------------------------
# Main
# ----------------------------
def main():
    print("[i] Loading sources…")
    feeds = load_sources(SOURCES_YML)

    print("[i] Fetching RSS items…")
    items = fetch_items(feeds)
    if not items:
        die("No items fetched from RSS sources. Check sources.yml or network access.")

    print(f"[i] Ranking {len(items)} items…")
    top = rank_items(items, limit=12)

    print("[i] Calling OpenAI to compose newsletter…")
    draft = summarize_with_openai(top)

    print("[i] Enforcing quality gates…")
    enforce_quality(draft)

    print("[i] Writing outputs…")
    write_outputs(draft)

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        die(str(e))
