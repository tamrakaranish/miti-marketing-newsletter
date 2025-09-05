# 🔧 Newsletter Configuration

This document explains how to configure the AI Newsletter system.

## 📱 Slack Channels

The newsletter can publish to different Slack channels based on the environment:

### **Method 1: GitHub Repository Variables** (Recommended)

Set these variables in your GitHub repository settings:

1. **Go to**: Repository → Settings → Secrets and variables → Actions → Variables tab
2. **Add these variables**:

| Variable Name | Default Value | Description |
|---------------|---------------|-------------|
| `SLACK_CHANNEL_TEST` | `#ai-publish-test` | Test environment Slack channel |
| `SLACK_CHANNEL_PRODUCTION` | `#mitigram-ai` | Production environment Slack channel |

### **Method 2: Direct Edit** (For quick changes)

If you need to change channels quickly, edit these lines in `.github/workflows/publish.yml`:

```yaml
# Around line 35
echo "📱 Slack channel: ${{ vars.SLACK_CHANNEL_TEST || '#ai-publish-test' }}"

# Around line 39  
echo "📱 Slack channel: ${{ vars.SLACK_CHANNEL_PRODUCTION || '#mitigram-ai' }}"

# Around line 199
SLACK_CHANNEL: ${{ steps.env.outputs.environment == 'production' && (vars.SLACK_CHANNEL_PRODUCTION || '#mitigram-ai') || (vars.SLACK_CHANNEL_TEST || '#ai-publish-test') }}
```

## 🔐 Required Secrets

Make sure these secrets are set in GitHub repository settings:

| Secret Name | Description | Where to Get |
|-------------|-------------|--------------|
| `SLACK_BOT_TOKEN` | Slack app bot token | Slack App settings |
| `OPENAI_API_KEY` | OpenAI API key | OpenAI platform |
| `CONFLUENCE_BASE_URL` | Confluence base URL | Your Atlassian instance |
| `CONFLUENCE_USER` | Confluence user email | Atlassian account |
| `CONFLUENCE_API_TOKEN` | Confluence API token | Atlassian account settings |
| `CONFLUENCE_SPACE_KEY` | Confluence space key | Space settings |
| `PR_TOKEN` | GitHub token for PRs | GitHub settings |

## 📊 RSS Sources

Edit newsletter sources in `sources.yml`:

```yaml
sources:
  "Trade Finance & Fintech":
    - https://example.com/feed.xml
  "AI & Technology":
    - https://another-feed.com/rss
```

## 🤖 AI Model Configuration

Edit model settings in `scripts/generate.py`:

```python
OPENAI_MODEL = "gpt-5-mini"  # Model to use
# Temperature is set to default (1.0) for gpt-5-mini
```

## 📅 Schedule Configuration

Edit generation schedule in `.github/workflows/newsletter.yml`:

```yaml
schedule:
  - cron: "0 6 * * 3"  # Wednesdays 07:00 CET (06:00 UTC)
```

## 🎯 Environment Behavior

| Trigger | Environment | Slack Channel |
|---------|-------------|---------------|
| **PR Merge** | Production | `SLACK_CHANNEL_PRODUCTION` |
| **Manual Generate + Test** | Test | `SLACK_CHANNEL_TEST` |
| **Manual Generate + Production** | Production | `SLACK_CHANNEL_PRODUCTION` |
| **Manual Publish + Test** | Test | `SLACK_CHANNEL_TEST` |
| **Manual Publish + Production** | Production | `SLACK_CHANNEL_PRODUCTION` |

---

*This configuration system makes the newsletter easy to customize without touching workflow code!* 🎯
