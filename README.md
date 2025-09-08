# Trade Finance Newsletter Automation

Automated trade finance and fintech newsletter system for Product Marketing. This system curates, summarizes, and generates bi-weekly newsletters focused on trade finance industry developments for customers, prospects, and stakeholders.

## 🎯 Purpose

Support Product Marketing with industry intelligence by:
- Providing trade finance and fintech market insights
- Delivering competitive landscape updates
- Sharing industry trends and opportunities
- Positioning thought leadership in the trade finance space

## 🚀 How It Works

```mermaid
flowchart LR
    A["Trade Finance<br/>RSS Sources"] --> B["Newsletter<br/>Generation"]
    
    B --> C["⏰ Bi-weekly<br/>(Tuesday Cron)"]
    B --> D["🚀 Manual<br/>(Urgent News)"]
    
    C --> E["newsletter/2025-01-15_slack.txt<br/>📰 Scheduled Newsletter"]
    D --> F["newsletter/2025-01-15-manual-HHMMSS_slack.txt<br/>🚀 Urgent Newsletter"]
    
    E --> G["📱 Direct Post to<br/>Slack Channel"]
    F --> G
    
    G --> H["✅ Product Marketing<br/>Review & Distribute"]
```

### Generation Modes

#### **⏰ Scheduled Mode (Bi-weekly)**
1. **Bi-weekly Trigger** - Every other Tuesday at 9:00 AM UTC
2. **Creates**: `newsletter/2025-01-15_slack.txt` (Slack format)
3. **Auto-posts** directly to Slack channel
4. **Best for**: Regular bi-weekly newsletters

#### **🚀 Manual Mode (Urgent)**
1. **Manual Trigger** via GitHub Actions
2. **Creates**: `newsletter/2025-01-15-manual-HHMMSS_slack.txt`
3. **Posts immediately** to Slack channel
4. **Best for**: Breaking news, urgent updates

### Workflow Steps
1. **Feed Fetching** - Pulls latest content from trade finance and fintech sources
2. **Content Ranking** - Scores items based on trade finance relevance and market impact
3. **AI Summarization** - OpenAI GPT-5-mini creates newsletter draft for marketing audience
4. **Quality Gates** - Validates source links and required sections
5. **Direct Publishing** - Posts formatted newsletter directly to Slack channel
6. **Human Review** - Product Marketing team reviews and distributes as needed

## 📋 Setup Instructions

### 1. Repository Setup
```bash
# Directory structure:
miti-marketing-newsletter/
├── .github/workflows/
│   └── trade-finance-newsletter.yml  # Simplified workflow
├── scripts/
│   ├── generate.py       # Main generation script
│   └── format_slack.py   # Slack formatting utility
├── sources.yml           # RSS feed configuration (trade finance focused)
├── requirements.txt      # Python dependencies
├── newsletter/           # Auto-created output directory
└── README.md
```

### 2. GitHub Configuration

#### Required Secrets
Add these in **Settings → Secrets and Variables → Actions → Secrets**:
- `OPENAI_API_KEY` - Your OpenAI API key with GPT-5-mini access
- `SLACK_BOT_TOKEN` - Slack app bot token for posting newsletters

#### Required Variables
Add these in **Settings → Secrets and Variables → Actions → Variables**:
- `SLACK_CHANNEL` - Target Slack channel (e.g., `#anish-ai-new`, `#product-marketing-ai`)

#### Repository Permissions
Ensure GitHub Actions has permission to:
- Read repository contents
- Access secrets (Settings → Actions → General → Workflow permissions)

### 3. Slack Channel Configuration

#### To Set the Target Channel:
1. Go to **Settings → Secrets and Variables → Actions → Variables**
2. Click **"New repository variable"**
3. Name: `SLACK_CHANNEL`
4. Value: Your desired channel (e.g., `#anish-ai-new`, `#product-marketing-ai`)
5. Click **"Add variable"**

**Note**: The channel name must include the `#` prefix. This variable is required for the workflow to function.

### 4. Customization

#### RSS Sources (`sources.yml`)
Current sources focus on trade finance and fintech:
- **Finextra** - Financial technology news and analysis
- **Trade Finance Global** - Trade finance industry updates
- **TLDR Fintech** - Fintech news digest

*Product Marketing team will provide additional sources as needed.*

#### Newsletter Template
The AI generates structured content with these sections:
1. **Market Intelligence** - Key trade finance and fintech developments
2. **Industry Impact** - Strategic implications for the trade finance ecosystem  
3. **Customer Opportunities** - How trends create opportunities for businesses
4. **Competitive Landscape** - Brief updates on competitor moves and market positioning
5. **Market Outlook** - Forward-looking insights and strategic recommendations

## 🔧 Manual Execution

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-api-key-here"

# Generate newsletter
cd scripts
python generate.py

# For urgent newsletters (adds timestamp)
MANUAL_MODE=1 python generate.py
```

### GitHub Actions Manual Workflow

#### 📰 Generate Urgent Newsletter
1. Go to **Actions → Generate Trade Finance Newsletter → Run workflow**
2. Check **"Generate urgent newsletter"** for immediate posting
3. Newsletter will be generated and posted directly to configured Slack channel

#### ⏰ Scheduled Newsletter
- Runs automatically every other Tuesday at 9:00 AM UTC
- No manual intervention required
- Posts directly to configured Slack channel

## 📊 Quality Controls

### Automated Validation
- **Source Links**: Validates working URLs for credibility
- **Required Sections**: Ensures all newsletter sections are present
- **Content Scoring**: Prioritizes trade finance and fintech relevant content
- **Length Control**: Maintains 350-400 word target for readability

### Human Review Process
- Newsletter posts directly to configured Slack channel
- Product Marketing team reviews content in Slack
- Team makes adjustments and distributes manually as needed
- No technical workflow required - simple Slack-based review

## 🚀 Current Features

### ✅ Implemented
- **Bi-weekly Scheduling** - Automated generation every other Tuesday
- **Manual Generation** - Urgent newsletter capability with timestamp
- **Configurable Slack Publishing** - Posts to configurable channel via GitHub variable
- **Trade Finance Focus** - Curated sources specific to trade finance and fintech
- **Marketing Audience** - Content tailored for customers, prospects, and stakeholders
- **Simplified Workflow** - No PR reviews or Confluence - straight to Slack
- **Smart Content Ranking** - Prioritizes trade finance relevance and market impact
- **Quality Validation** - Ensures working links and complete sections
- **Robust Error Handling** - Timeout protection and retry logic for API calls

### 🔮 Future Enhancements  
- **Additional Sources** - More trade finance feeds as provided by Product Marketing
- **Engagement Tracking** - Monitor Slack engagement and feedback
- **Email Integration** - Optional email distribution for external stakeholders
- **Content Analytics** - Track trending topics and industry focus areas

## 🛠️ Troubleshooting

### Common Issues

**Newsletter Generation Fails**
- Check OpenAI API key is valid and has sufficient credits
- Verify GPT-5-mini model access (or change to gpt-4o-mini in `scripts/generate.py`)
- Review RSS sources are accessible in `sources.yml`
- Check GitHub Actions logs for specific errors

**Slack Posting Issues**
- Verify `SLACK_CHANNEL` GitHub variable is set with the correct channel name
- Verify Slack bot is added to the target channel specified in `SLACK_CHANNEL` variable
- Check `SLACK_BOT_TOKEN` secret is configured correctly
- Ensure bot has permission to post messages in the channel
- Review workflow logs for Slack API errors

**Bi-weekly Schedule Issues**
- Check if week number logic needs adjustment for your desired start date
- Verify cron schedule in `.github/workflows/trade-finance-newsletter.yml`
- Use manual trigger to override schedule when needed

## 📚 Documentation

- **[README.md](README.md)** - This setup and usage guide
- **[FEED_VALIDATION_GUIDE.md](FEED_VALIDATION_GUIDE.md)** - Guide for validating RSS feeds

## 📧 Support

For issues with the newsletter system:
1. Check GitHub Actions workflow logs
2. Test manual execution locally first  
3. Verify all secrets are properly configured
4. Contact Product Marketing team for source adjustments

---

*Supporting Product Marketing with automated trade finance industry intelligence* 📈