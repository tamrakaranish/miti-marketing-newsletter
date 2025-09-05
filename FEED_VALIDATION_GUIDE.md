# Feed Validation Guide

This guide explains how to validate RSS feeds before adding them to your newsletter sources.

## Prerequisites

- Python installed (you already have this)
- `feedparser` library: `pip install feedparser`
- Basic terminal/command prompt usage

## Quick Validation Steps

### 1. Open Terminal in Project Directory
```bash
cd C:\Development\miti-ai-newsletter
python
```

### 2. Test a Single Feed
```python
import feedparser

# Replace with the feed URL you want to test
url = "https://example.com/feed.xml"
parsed = feedparser.parse(url)

# Check the results
print("Status:", getattr(parsed, 'status', 'No status'))
print("Parsing errors:", getattr(parsed, 'bozo', 0))
print("Number of articles:", len(parsed.entries))

# Look at first article if available
if len(parsed.entries) > 0:
    first = parsed.entries[0]
    print("Title:", getattr(first, 'title', 'No title'))
    print("Link:", getattr(first, 'link', 'No link'))
    print("Summary:", getattr(first, 'summary', 'No summary')[:100] + "...")
    print("Published:", getattr(first, 'published', 'No date'))
```

### 3. Batch Test Multiple Feeds
```python
import feedparser

# List of feeds to test
test_feeds = [
    ("Feed Name 1", "https://example1.com/feed.xml"),
    ("Feed Name 2", "https://example2.com/rss"),
    # Add more feeds here
]

for name, url in test_feeds:
    print(f"\n=== Testing {name} ===")
    parsed = feedparser.parse(url)
    
    status = getattr(parsed, 'status', 'No status')
    errors = getattr(parsed, 'bozo', 0)
    article_count = len(parsed.entries)
    
    print(f"Status: {status}")
    print(f"Errors: {errors}")
    print(f"Articles: {article_count}")
    
    if article_count > 0:
        first = parsed.entries[0]
        title = getattr(first, 'title', 'No title')[:50]
        print(f"Sample: {title}...")
        print("✅ WORKING")
    else:
        print("❌ BROKEN")

# Exit Python when done
exit()
```

## What Makes a Good Feed?

### ✅ Success Indicators
- **Status: 200** - Feed URL is accessible
- **Errors: 0** - XML is properly formatted
- **Articles: 5+** - Has recent content
- **Valid titles and links** - Not empty or corrupted
- **Recent dates** - Published in last few weeks/months

### ❌ Warning Signs
- **Status: 404** - Feed doesn't exist
- **Status: 403** - Feed is blocked/private
- **Errors: 1** - Malformed XML (may still work)
- **Articles: 0** - No content available
- **Missing fields** - No titles, links, or summaries

## Content Requirements for Your Newsletter

Your feeds should contain articles with these relevant keywords:

### Core AI
- ai, artificial intelligence, model, models, llm, genai, machine learning

### Trade Finance & Banking
- trade finance, trade, commodity, letter of credit, swift, iso 20022
- payments, cross-border, fx, treasury, bank, banking, supply chain finance

### Compliance & Regulation
- aml, kyc, sanctions, ofac, basel, governance, risk, compliance
- regtech, fincrime, regulation, regulatory, eu ai act

### Business Context
- customer, b2b, saas

## Adding Validated Feeds

Once you've confirmed a feed works:

1. Add it to `sources.yml` under the appropriate category:
```yaml
feeds:
  # Trade Finance & Fintech
  - name: Your New Source
    url: https://validated-feed-url.com/rss
```

2. Test the newsletter generation:
```bash
python scripts/generate.py
```

3. Check that your new source appears in the ranked articles.

## Troubleshooting

### Common Issues

**"No module named feedparser"**
```bash
pip install feedparser
```

**SSL Certificate errors**
- Usually temporary - try again later
- Feed may work in GitHub Actions even if failing locally

**Bozo errors but articles still appear**
- Many feeds have minor XML issues but still work
- Test with actual newsletter generation to confirm

**Empty results from working websites**
- Website might not have an RSS feed
- Look for `/feed`, `/rss`, `/feed.xml`, `/rss.xml` endpoints
- Check website footer for RSS links

### Getting Help

If you're unsure about a feed:
1. Check if articles appear relevant to your newsletter topics
2. Verify the feed updates regularly (check publication dates)
3. Test with the full newsletter generation process
4. Ask on forums or check the website's documentation for official RSS URLs

## Examples from Current Sources

### Working Feed (Finextra)
```
Status: 200
Errors: 0
Articles: 59
Sample: ID.me hits $2bn valuation on funding to tackle AI fraud...
✅ WORKING
```

### Broken Feed (Example)
```
Status: 404
Errors: 1
Articles: 0
❌ BROKEN
```
