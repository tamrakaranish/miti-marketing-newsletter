#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a draft AI newsletter markdown file from curated RSS sources.

Outputs: newsletter/<YYYY-MM-DD>.md
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
OUTFILE = OUTDIR / f"{DATE}.md"

# Model & API endpoint (adjust if your org uses a different model)
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"   # keep in sync with your org policy

# Hard rules for output quality
MAX_WORDS = 400        # hard ceiling to keep it concise
REQUIRED_MIN_LINKS = 3 # require at least N URLs in the draft


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
    # Enhanced scoring for PLD transformation relevance
    KEYS = {
        # High priority - core AI/tech terms
        ("ai", "artificial intelligence", "machine learning", "llm", "gpt", "automation"): 3,
        # Medium priority - business transformation
        ("product-led", "pld", "transformation", "agile", "devops", "innovation"): 2,
        # Standard priority - industry terms  
        ("fintech", "trade", "compliance", "regulation", "customer", "b2b", "saas"): 1,
        # Bonus terms - specific to company context
        ("cross-functional", "autonomous", "data-driven", "transparency"): 2
    }
    
    scored = []
    for it in items:
        text = (it["title"] + " " + it["summary"]).lower()
        score = 0
        
        # Calculate weighted score based on keyword categories
        for keywords, weight in KEYS.items():
            for keyword in keywords:
                if keyword in text:
                    score += weight
        
        # Prefer items with links
        if it["link"]:
            score += 1
            
        # Boost recent items (basic recency scoring)
        if it.get("published"):
            try:
                # Simple boost for items from last 7 days
                from dateutil import parser
                pub_date = parser.parse(it["published"])
                days_old = (dt.datetime.now(pub_date.tzinfo) - pub_date).days
                if days_old <= 7:
                    score += 2
                elif days_old <= 30:
                    score += 1
            except:
                pass  # Skip if date parsing fails
                
        scored.append((score, it))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:limit]]


def require_api_key() -> str:
    """Fail fast with a clear message if the key is missing."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it in GitHub → Repo → Settings → Secrets → Actions."
        )
    return api_key


def summarize_with_openai(selected_items):
    api_key = require_api_key()

    system_msg = (
        "You produce a short internal AI newsletter for Mitigram, a trade-finance SaaS company transitioning from "
        "Feature Factory to Product-Led Development (PLD). Your audience includes business, tech, product, and design teams. "
        "Focus on AI developments that could impact autonomous team decision-making, cross-functional collaboration, "
        "and data-driven product development. Be factual, include source links, avoid speculation and personal data. "
        "Connect AI trends to business value and transformation opportunities."
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

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

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
    # Word cap
    words = re.findall(r"\b\w+\b", md_text)
    if len(words) > MAX_WORDS:
        die(f"Draft too long ({len(words)} words). Keep under {MAX_WORDS} words.")

    # Require at least N URLs (rudimentary but effective)
    links = re.findall(r"https?://\S+", md_text)
    if len(links) < REQUIRED_MIN_LINKS:
        die(f"Draft contains too few links ({len(links)}). Require at least {REQUIRED_MIN_LINKS} source URLs.")

    # Basic sanity: must have the core sections
    required_headers = ("AI in Trade Finance", "Tip of the Week", "Quick Hits")
    for h in required_headers:
        if h.lower() not in md_text.lower():
            die(f"Draft missing required section heading: '{h}'.")


def write_output(md_text: str):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with OUTFILE.open("w", encoding="utf-8") as f:
        f.write(f"# MitiMind – {DATE}\n\n")
        f.write(md_text)
        f.write("\n\n— Auto‑draft by AI agent, please review before publishing.\n")
    print(f"[OK] Draft written to {OUTFILE}")


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

    print("[i] Writing output…")
    write_output(draft)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        # Explicit for missing secrets etc.
        die(str(e))
