#!/usr/bin/env python3

import feedparser
import sys

feeds = [
    ('GTR', 'https://www.gtreview.com/rss'),
    ('Trade Finance Global', 'https://www.tradefinanceglobal.com/posts/category/news/feed/'),
    ('Trade Treasury Payments', 'https://tradetreasurypayments.com/posts/category/news/feed'),
    ('TXF', 'https://www.txfnews.com/rss'),
    ('Supply Chain Digital', 'https://supplychaindigital.com/feed'),
    ('Treasury Management', 'https://treasury-management.com/feed'),
    ('Finextra Research', 'https://www.finextra.com/rss/headlines.aspx'),
    ('Fintech Finance News', 'https://ffnews.com/feed/'),
    ('PYMNTS', 'https://www.pymnts.com/feed/'),
    ('The Banker', 'https://www.thebanker.com/rss'),
    ('Financial Times Global Trade', 'https://www.ft.com/global-trade?format=rss')
]

print('Testing RSS feeds...\n')

working_feeds = []
broken_feeds = []

for name, url in feeds:
    print(f'Testing {name}...')
    try:
        parsed = feedparser.parse(url)
        status = getattr(parsed, 'status', 'No status')
        errors = getattr(parsed, 'bozo', 0)
        article_count = len(parsed.entries)
        
        if article_count > 0 and status != 404:
            first = parsed.entries[0]
            title = getattr(first, 'title', 'No title')[:50]
            print(f'  ✅ WORKING - Status: {status}, Articles: {article_count}')
            print(f'  Sample: {title}...')
            working_feeds.append((name, url))
        else:
            print(f'  ❌ BROKEN - Status: {status}, Articles: {article_count}')
            broken_feeds.append((name, url))
    except Exception as e:
        print(f'  ❌ ERROR - {str(e)[:50]}...')
        broken_feeds.append((name, url))
    print()

print(f'\n=== SUMMARY ===')
print(f'Working feeds: {len(working_feeds)}')
print(f'Broken feeds: {len(broken_feeds)}')

if working_feeds:
    print(f'\n✅ WORKING FEEDS:')
    for name, url in working_feeds:
        print(f'  - {name}: {url}')

if broken_feeds:
    print(f'\n❌ BROKEN FEEDS:')
    for name, url in broken_feeds:
        print(f'  - {name}: {url}')
