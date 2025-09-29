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
import time
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

# Simple file naming - always use clean date format
OUT_SLACK = OUTDIR / f"{DATE}_slack.txt"
print(f"[i] Generating newsletter: {OUT_SLACK.name}")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-5-mini"   # upgraded model for better analysis

MAX_WORDS = 400
REQUIRED_MIN_LINKS = 3

# Custom message section (can be edited for special announcements)
# Can be overridden with CUSTOM_MESSAGE environment variable for testing
CUSTOM_MESSAGE = os.environ.get("CUSTOM_MESSAGE", "")

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
    KEYS = (
        # Core trade finance terms (highest priority)
        "trade finance", "trade-finance", "letter of credit", "lc", "documentary credit", "bill of lading",
        "export finance", "export financing", "import finance", "export lc", "export letter of credit",
        "bank guarantee", "digital guarantee", "trade credit", "guarantees", "trade insurance",
        
        # International trade activities
        "international trade", "global trade", "export", "exporters", "trade flows", "cross-border trade",
        "export compliance", "export credit insurance", "export fraud",
        
        # Trade regulations and policies  
        "tariff", "sanctions", "wto ruling", "custom regulation", "export control", "incoterms",
        "trade policy", "trade finance regulation", "trade finance policy",
        
        # Supply chain and logistics
        "shipping delays", "freight rates", "logistics costs", "global supply chain", "supply chain finance",
        
        # Financial risk and management
        "risk management", "payment risk", "currency risk", "working capital", "geopolitical risk",
        "accounts receivable", "receivables", "receivables financing", "documentation errors", "trade finance gap",
        
        # Modern trade finance trends
        "green trade", "digital trade", "ai in trade", "treasury", "swift", "iso 20022",
        "sustainable finance", "esg", "carbon credits", "trade corridor", "digitization",
        
        # Key players and platforms
        "contour", "we.trade", "tradelens", "dltledgers", "komgo", "tradeix",
        
        # General fintech (lower priority)
        "fintech", "financial technology", "digital payments", "api", "open banking", "blockchain",
        "embedded finance", "b2b payments", "working capital", "invoice financing"
    )
    
    # Keywords to avoid or penalize
    AVOID_KEYS = (
        "stock trading", "day trading", "forex trading", "crypto", "cryptocurrency", "bitcoin",
        "options trading", "retail trading", "investment trading", "algorithmic trading"
    )
    
    # Score all items
    scored = []
    for it in items:
        text = (it["title"] + " " + it["summary"]).lower()
        
        # Positive scoring for relevant keywords
        score = sum(k in text for k in KEYS)
        if it["link"]:
            score += 1
        
        # Penalize items with avoided keywords (financial trading)
        avoid_penalty = sum(k in text for k in AVOID_KEYS)
        score = max(0, score - (avoid_penalty * 2))  # Heavy penalty for avoid keywords
        
        # Penalize arXiv to ensure source diversity (they tend to dominate with academic keywords)
        if "arxiv.org" in it.get("link", ""):
            score = score * 0.7  # Reduce arXiv scores by 30%
            
        scored.append((score, it))
    
    # Sort by score first
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Apply source diversity selection - ensure no single source dominates
    selected = []
    source_count = {}
    
    for score, item in scored:
        if len(selected) >= limit:
            break
            
        # Extract source from the item (usually in feed metadata or link domain)
        source = item.get("source", "")
        if not source and item.get("link"):
            # Extract domain as source identifier
            try:
                from urllib.parse import urlparse
                source = urlparse(item["link"]).netloc.replace("www.", "")
            except:
                source = "unknown"
        
        # Limit per source: max 1 item from any single source for better diversity
        current_count = source_count.get(source, 0)
        if current_count < 1:
            selected.append(item)
            source_count[source] = current_count + 1
    
    # If we didn't get enough items due to source limits, fill with remaining high-score items
    if len(selected) < limit:
        remaining_needed = limit - len(selected)
        already_selected_links = {item.get("link") for item in selected}
        
        for score, item in scored:
            if len(selected) >= limit:
                break
            if item.get("link") not in already_selected_links:
                selected.append(item)
                already_selected_links.add(item.get("link"))
    
    return selected[:limit]

def require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it in GitHub → Repo → Settings → Secrets → Actions.")
    return api_key

def summarize_with_openai(selected_items):
    api_key = require_api_key()

    system_msg = (
        "You produce a trade finance and fintech newsletter for a marketing audience. "
        "Your readers include existing customers, potential clients, industry stakeholders, and business decision-makers. "
        "Focus on market trends, business opportunities, industry developments, and competitive landscape. "
        "Write in a professional, engaging tone that demonstrates thought leadership and market expertise. "
        "Emphasize business value, market implications, and strategic opportunities. Be factual and include source links."
    )
    user_payload = {
        "date": DATE,
        "instructions": dedent("""
            Output only in this exact Slack format:

            *{Headline insight/trend}* – {one-line interpretation}

            {Optional contextual expansion sentence, may include *bold* emphasis for key forces or dynamics. Keep to max 2 sentences.}

            • {Entity/Company/Deal} {action/outcome} {amount/metric} – <{Source URL}|{Source Name}>  
            • {Entity/Company/Deal} {action/outcome} {amount/metric} – <{Source URL}|{Source Name}>  
            • {Entity/Company/Deal} {action/outcome} {amount/metric} – <{Source URL}|{Source Name}>

            Rules:
            - Exactly one bold headline line, followed by one short interpretation.
            - Optional context line allowed (max 2 sentences).
            - Use *bold* only for the headline and optional emphasis in the context line.
            - Provide exactly 3-5 bullet points for optimal scanning.
            - Each bullet must start with "• " and end with "– <URL|Source Name>".
            - Do not display raw URLs — they must be hidden behind the source name.
            - No extra headings, intro, or outro text.
            - No emojis or commentary outside the structure.
            - Focus on trade finance, fintech, and related industry developments.
            - CRITICAL: Use different sources for each bullet point - no source should appear twice.
            - Include specific numbers/amounts when available (funding, deals, percentages).
            - Write for a marketing audience: professional, business-focused tone.
            - Keep total content under 200 words for quick scanning.
            - Start each bullet with concrete entity/company name when possible.
        """).strip(),
        "items": selected_items
    }

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Simple retry logic - try twice with a brief delay
    for attempt in range(2):
        try:
            resp = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(body), timeout=180)
            break  # Success, exit retry loop
        except requests.exceptions.RequestException as e:
            if attempt == 1:  # Final attempt failed
                die(f"OpenAI API network error after retries: {e}")
            print(f"[WARNING] OpenAI API timeout on attempt {attempt + 1}, retrying once in 5 seconds...")
            time.sleep(5)
    
    if resp.status_code >= 300:
        try:
            error_data = resp.json()
            error_msg = error_data.get('error', {}).get('message', resp.text[:500])
        except:
            error_msg = resp.text[:500]
        die(f"OpenAI API error {resp.status_code}: {error_msg}")
    
    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except KeyError as e:
        die(f"Unexpected OpenAI response structure - missing field: {e}")
    except Exception as e:
        die(f"Error parsing OpenAI response: {e} | Response: {resp.text[:800]}")
    return content.strip()

def enforce_quality(md_text: str):
    # Check for the new simple format: headline + optional context + bullets with Slack links
    
    print(f"[DEBUG] Checking content for new simple format...")
    print(f"[DEBUG] Content preview (first 1000 chars):")
    print(f"{md_text[:1000]}...")
    print(f"[DEBUG] Full content length: {len(md_text)} characters")
    
    # Check for required elements in the new format
    headline_pattern = re.findall(r"^\*[^*]+\*\s*–", md_text, re.MULTILINE)
    bullet_lines = re.findall(r"^•.*$", md_text, re.MULTILINE)
    slack_links = re.findall(r"<https?://[^|>]+\|[^>]+>", md_text)
    
    print(f"[DEBUG] Found patterns:")
    print(f"[DEBUG] - Headlines with * and –: {headline_pattern}")
    print(f"[DEBUG] - Bullet lines: {bullet_lines}")
    print(f"[DEBUG] - Slack-formatted links: {slack_links}")
    
    # Validate the new format
    if len(headline_pattern) < 1:
        die(f"Draft missing required headline format '*text* – interpretation'. Found {len(headline_pattern)} headlines.")
    
    if len(bullet_lines) < 3 or len(bullet_lines) > 5:
        die(f"Draft contains wrong number of bullet points ({len(bullet_lines)}). Require exactly 3-5 bullet points.")
    
    if len(slack_links) < 3:
        die(f"Draft contains too few Slack-formatted links ({len(slack_links)}). Require at least 3 links in format <URL|Source>.")
    
    # Check for source diversity - no source should appear twice
    sources_in_bullets = []
    for bullet in bullet_lines:
        source_match = re.search(r"<[^|>]+\|([^>]+)>", bullet)
        if source_match:
            sources_in_bullets.append(source_match.group(1))
    
    duplicate_sources = [s for s in sources_in_bullets if sources_in_bullets.count(s) > 1]
    if duplicate_sources:
        die(f"Draft contains duplicate sources: {duplicate_sources}. Each bullet must use a different source.")
    
    # Log information
    words = re.findall(r"\b\w+\b", md_text)
    print(f"[INFO] Newsletter word count: {len(words)} words")
    print(f"[INFO] Found {len(headline_pattern)} headlines, {len(bullet_lines)} bullets, {len(slack_links)} Slack links")
    print(f"[INFO] Quality check passed - new simple format validated")

# ---------- Slack formatting ----------
LINK_MD = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
HEADER_MD = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_MD = re.compile(r"^\s*-\s+")

def add_emoji_for_heading(title: str) -> str:
    t = title.strip().lower()
    
    # Product Marketing newsletter sections
    if "market intelligence" in t:
        return f"📊 {title}"
    if "industry impact" in t:
        return f"🏭 {title}"
    if "customer opportunities" in t:
        return f"🎯 {title}"
    if "competitive landscape" in t:
        return f"🏆 {title}"
    if "market outlook" in t:
        return f"🔮 {title}"
    
    # Legacy sections (for compatibility)
    if "business impact" in t:
        return f"💰 {title}"
    if "what different teams should know" in t:
        return f"👥 {title}"
    if "market pulse" in t:
        return f"⚡ {title}"
    if "recommended actions" in t:
        return f"📋 {title}"
        
    # Legacy sections (for compatibility)
    if "what this means for us" in t:
        return f"🎯 {title}"
    if "implementation focus" in t:
        return f"💡 {title}"
    if "quick hits" in t:
        return f"⚡ {title}"
    if "next steps" in t:
        return f"📋 {title}"
    
    # Legacy sections (for compatibility)
    if "ai in trade finance" in t:
        return f"🚀 {title}"
    if "tip of the week" in t:
        return f"💡 {title}"
    if "internal spotlight" in t:
        return f"🔍 {title}"
    if "cta" in t or "call to action" in t or "pilots" in t or "polls" in t:
        return f"📋 {title}"
    
    # Newsletter header
    if "mitimind" in t or "newsletter" in t:
        return f"🗞️ {title}"
    
    # Trade finance topics
    if any(word in t for word in ["trade", "finance", "payment", "banking", "swift"]):
        return f"💰 {title}"
    
    # AI/Tech topics  
    if any(word in t for word in ["ai", "artificial intelligence", "machine learning", "llm", "model"]):
        return f"🤖 {title}"
    
    # Business/Strategy topics
    if any(word in t for word in ["strategy", "business", "product", "innovation"]):
        return f"📈 {title}"
    
    return title

def convert_md_to_slack(markdown: str) -> str:
    lines = markdown.splitlines()
    out = []
    for ln in lines:
        m = HEADER_MD.match(ln)
        if m:
            title = m.group(2).strip()
            # Don't add emojis if they're already present
            if not title.startswith(('📊', '🎯', '💡', '⚡', '📋', '🚀', '🔍', '🗞️', '💰', '🤖', '📈')):
                title = add_emoji_for_heading(title)
            out.append(f"*{title}*")
            continue
        if BULLET_MD.match(ln):
            ln = BULLET_MD.sub("• ", ln)
        ln = LINK_MD.sub(r"<\2|\1>", ln)  # [text](url) -> <url|text>
        out.append(ln)
    return "\n".join(out)

def add_emojis_to_markdown(markdown: str) -> str:
    """Add emojis to Markdown headings."""
    lines = markdown.splitlines()
    out = []
    for ln in lines:
        m = HEADER_MD.match(ln)
        if m:
            level = m.group(1)  # ### or ## etc
            title = m.group(2).strip()
            # Add emoji to title, then reconstruct the heading
            emoji_title = add_emoji_for_heading(title)
            out.append(f"{level} {emoji_title}")
        else:
            out.append(ln)
    return "\n".join(out)

# ---------- Write outputs ----------
def write_outputs(md_body: str):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    header = f"🗞️ *Trade Finance Weekly* – {DATE}\n\n"
    
    # Add custom message if defined
    custom_message_section = ""
    if CUSTOM_MESSAGE and CUSTOM_MESSAGE.strip():
        # Add visual separators around the message
        custom_message_section = f"---\n\n{CUSTOM_MESSAGE.strip()}\n\n---\n\n"
    
    # Use the content as-is (no emojis needed for new simple format)
    md_full = header + custom_message_section + md_body + "\n\n_— Auto-generated newsletter for Product Marketing review_\n"
    
    # Quality check on full assembled text
    print("[i] Enforcing quality gates on assembled newsletter…")
    enforce_quality(md_full)
    
    # AI already generates Slack-ready format, no conversion needed
    slack_text = md_full
    with OUT_SLACK.open("w", encoding="utf-8") as f:
        f.write(slack_text)
    print(f"[OK] Slack newsletter written to {OUT_SLACK}")

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

    print("[i] Writing outputs…")
    write_outputs(draft)

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        die(str(e))
