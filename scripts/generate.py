import os, re, json, datetime, textwrap, hashlib
import feedparser, requests

OUTDIR = "newsletter"
SOURCES = "sources.yml"
DATE = datetime.date.today().isoformat()
OUTFILE = f"{OUTDIR}/{DATE}.md"

def clean(text): return re.sub(r"\s+", " ", text or "").strip()

def fetch_feeds():
    import yaml
    with open(SOURCES) as f:
        cfg = yaml.safe_load(f)
    items = []
    for feed in cfg["feeds"]:
        d = feedparser.parse(feed["url"])
        for e in d.entries:
            items.append({
                "source": feed["name"],
                "title": clean(getattr(e, "title", "")),
                "link": getattr(e, "link", ""),
                "summary": clean(getattr(e, "summary", "") or getattr(e, "description", "")),
                "published": getattr(e, "published", "")
            })
    return dedupe(items)

def dedupe(items):
    seen = set(); out = []
    for it in items:
        key = hashlib.sha256((it["title"] + it["link"]).encode()).hexdigest()[:16]
        if key not in seen:
            seen.add(key); out.append(it)
    return out

def openai_summarize(selected):
    # Compose the system+user prompt
    system = (
      "You are producing a short internal AI newsletter for a trade finance SaaS company. "
      "Keep factual, cite the source links inline, and avoid speculation."
    )
    user = {
      "date": DATE,
      "items": selected,
      "instructions": textwrap.dedent("""
        Write under 350 words with sections:
        1) AI in Trade Finance (1 item) + 'What this means for us'
        2) Tip of the Week
        3) Internal Spotlight (if none provided, suggest a small experiment)
        4) Quick Hits (3 bullets)
        5) CTA for pilots/polls

        Rules:
        - Include the source link next to each claim (e.g., [Source](URL)).
        - If uncertain, say so or exclude.
        - No confidential info. No personal data.
      """)
    }
    # Call the OpenAI API (simple completion)
    import json, urllib.request
    api_key = os.environ["OPENAI_API_KEY"]
    payload = {
      "model": "gpt-4o-mini",  # or your preferred current model
      "messages": [
        {"role":"system","content":system},
        {"role":"user","content":json.dumps(user)}
      ],
      "temperature": 0.2
    }
    req = urllib.request.Request(
      "https://api.openai.com/v1/chat/completions",
      data=json.dumps(payload).encode(),
      headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
      data = json.load(resp)
    return data["choices"][0]["message"]["content"]

def rank(items):
    # Minimal heuristic: prefer titles with "AI", "model", "policy", "fintech", "trade"
    KEYS = ["ai","model","fintech","trade","compliance","regulation","customer"]
    scored = []
    for it in items:
        score = sum(k in it["title"].lower() + " " + it["summary"].lower() for k in KEYS)
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:12]]  # keep top 12 for LLM selection

def main():
    items = fetch_feeds()
    top = rank(items)
    md = openai_summarize(top)
    os.makedirs(OUTDIR, exist_ok=True)
    with open(OUTFILE, "w") as f:
        f.write(f"# MitiMind – {DATE}\n\n")
        f.write(md)
        f.write("\n\n— Auto‑draft by AI agent, please review before publishing.\n")
    print("Draft written to", OUTFILE)

if __name__ == "__main__":
    main()
