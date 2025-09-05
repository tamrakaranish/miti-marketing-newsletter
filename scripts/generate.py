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
OPENAI_MODEL = "gpt-5-mini"   # upgraded model for better analysis

MAX_WORDS = 400
REQUIRED_MIN_LINKS = 3

# Custom message section (can be edited for special announcements)
CUSTOM_MESSAGE = """
🎉 **Major Newsletter Upgrades - Issue #2**

After our first newsletter, we've already implemented massive improvements to deliver more strategic value:

**📊 Better Content Curation**: Added premium sources (TLDR AI, Fintech, Product) and enhanced feed validation for higher-quality, more relevant content.

**🎯 Strategic Focus**: Restructured sections to be more actionable - "Market Intelligence" with business implications, "Implementation Focus" for practical guidance, and "Next Steps" for clear actions.

**🎓 Educational Approach**: Now includes context for technical terms and explains WHY developments matter, making complex AI/fintech concepts accessible to all team members.

**⚡ Visual Improvements**: Added emojis for better readability and enhanced formatting for both Slack and Confluence.

This newsletter now delivers maximum strategic value while building AI literacy across the team. **Share your feedback** - what topics would you like covered? What format works best? Help me make this even better!
"""

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
        # Core AI
        "ai", "artificial intelligence", "model", "models", "llm", "genai", "machine learning",
        # Trade finance and banking
        "trade finance", "trade-finance", "trade", "commodity", "letter of credit", "lc", "bill of lading",
        "swift", "iso 20022", "payments", "cross-border", "fx", "treasury", "bank", "banking", "supply chain finance",
        "invoice finance", "factoring",
        # Risk, compliance, regulation
        "aml", "kyc", "sanctions", "ofac", "basel", "governance", "risk", "compliance", "regtech", "fincrime",
        "regulation", "regulatory", "eu ai act",
        # Business context
        "customer", "b2b", "saas"
    )
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
        "Your audience includes product managers, engineers, and business stakeholders who may not be familiar with all AI/fintech concepts. "
        "When covering technical topics, provide brief educational context to help readers understand the significance. "
        "Be factual. Include source links next to claims. Avoid speculation and personal data."
    )
    user_payload = {
        "date": DATE,
        "instructions": dedent("""
            Write under 400 words using proper Markdown headings for sections:
            
            ## Market Intelligence
            (1-2 items) Major AI developments affecting fintech/trade finance. Focus on: new AI capabilities, regulatory changes, competitive moves, or technology breakthroughs that could impact our product roadmap.
            
            ## What This Means for Us
            Translate the market intelligence into specific implications for our trade finance SaaS platform. Consider: product opportunities, technical feasibility, competitive positioning, or regulatory compliance needs.
            
            ## Implementation Focus
            (Weekly insight) Practical advice for implementing AI in trade finance products. Topics could include: integration patterns, data requirements, risk management, customer adoption strategies, or technical best practices.
            
            ## Quick Hits
            (3 bullet points) Brief updates on: AI tools/frameworks, regulatory updates, competitor moves, or industry partnerships relevant to trade finance AI.
            
            ## Next Steps
            Suggest 1-2 specific actions the team should consider: research topics, pilot opportunities, vendor evaluations, or strategic discussions based on this week's intelligence.

            Rules:
            - DO NOT include a title or header - the title is already provided.
            - Use proper Markdown headings with ## for each section
            - Start directly with the first section content
            - Include the source link next to each claim (e.g., [Source](URL)).
            - Focus on business impact and actionability for a trade finance SaaS company
            - When mentioning technical concepts, AI models, or industry terms, provide brief context (e.g., "LLMs (Large Language Models, like ChatGPT)" or "KYC (Know Your Customer compliance)")
            - Explain why developments matter, not just what happened
            - Be specific about implications rather than generic
            - If uncertain about a claim, exclude it or mark it clearly
            - No confidential info. No personal data.
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
    try:
        resp = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(body), timeout=60)
    except requests.exceptions.RequestException as e:
        die(f"OpenAI API network error: {e}")
    
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
    words = re.findall(r"\b\w+\b", md_text)
    if len(words) > MAX_WORDS:
        die(f"Draft too long ({len(words)} words). Keep under {MAX_WORDS} words.")
    links = re.findall(r"https?://\S+", md_text)
    if len(links) < REQUIRED_MIN_LINKS:
        die(f"Draft contains too few links ({len(links)}). Require at least {REQUIRED_MIN_LINKS} source URLs.")
    for h in ("Market Intelligence", "What This Means for Us", "Quick Hits"):
        if h.lower() not in md_text.lower():
            die(f"Draft missing required section heading: '{h}'.")

# ---------- Slack formatting ----------
LINK_MD = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
HEADER_MD = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_MD = re.compile(r"^\s*-\s+")

def add_emoji_for_heading(title: str) -> str:
    t = title.strip().lower()
    
    # Main newsletter sections
    if "market intelligence" in t:
        return f"📊 {title}"
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
    header = f"# 🗞️ MitiMind – {DATE}\n\n"
    
    # Add custom message if defined
    custom_message_section = ""
    if CUSTOM_MESSAGE and CUSTOM_MESSAGE.strip():
        # Add visual separators around the message
        custom_message_section = f"---\n\n{CUSTOM_MESSAGE.strip()}\n\n---\n\n"
    
    # Add emojis to headings in the body content
    md_body_with_emojis = add_emojis_to_markdown(md_body)
    
    md_full = header + custom_message_section + md_body_with_emojis + "\n\n— Auto‑draft by AI agent, please contact the EMs for feedback.\n"
    
    # Markdown for PR/Confluence
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write(md_full)
    print(f"[OK] Markdown written to {OUT_MD}")
    
    # Slack-friendly text (emojis already applied via convert_md_to_slack)
    slack_text = convert_md_to_slack(md_full)
    with OUT_SLACK.open("w", encoding="utf-8") as f:
        f.write(slack_text)
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
