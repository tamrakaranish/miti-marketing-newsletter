# 🚀 Newsletter Staging Guide

A beginner-friendly guide to using the three-mode newsletter system: Scheduled, Manual Production, and Test modes.

## 📋 How the Three Modes Work

### **⏰ Scheduled Mode (Auto-Publish)**
- **Trigger**: Automatic every Wednesday 7:00 CET
- **File**: `newsletter/2025-01-15.md` 
- **Behavior**: Auto-publishes to production when PR merged
- **Best for**: Regular weekly newsletters

### **🚀 Manual Production Mode (Manual Control)**
- **Trigger**: Manual with "Production Mode" checkbox ✅
- **File**: `newsletter/2025-01-15-manual-HHMMSS-123.md`
- **Behavior**: Requires manual publish workflow
- **Best for**: Emergency posts, special announcements

### **🧪 Test Mode (Safe Experimentation)**
- **Trigger**: Manual without "Production Mode" (default)
- **File**: `newsletter/2025-01-15-test-HHMMSS-123.md`
- **Behavior**: Never auto-publishes, manual control only
- **Best for**: Testing, experiments, training

## 🎯 Environment Targeting

### **Test Environment**
- **Slack Channel**: Configurable via `SLACK_CHANNEL_TEST` GitHub Variable
- **Purpose**: Safe testing, drafts, experiments
- **Who sees it**: Only you and selected team members

### **Production Environment**  
- **Slack Channel**: Configurable via `SLACK_CHANNEL_PRODUCTION` GitHub Variable
- **Purpose**: Live newsletters for the whole company
- **Who sees it**: Everyone in the company

### **Confluence**: Both environments save to the same space with different page titles

## 🎯 How to Use

### **Option 1: Normal Production Flow**
1. **Wednesday**: AI generates newsletter → Creates PR
2. **Review & Merge PR** → Auto-publishes to **PRODUCTION**

### **🚨 Emergency Production Newsletter**
1. **Go to GitHub** → Actions → "Generate AI Newsletter"
2. **Click "Run workflow"**
3. **✅ Check "Generate production-ready newsletter"**
4. **Review PR** → Merge (safe, won't auto-publish)
5. **Actions** → "Publish Newsletter"
6. **Choose environment**: `production` → Publish

### **🧪 Testing & Experimentation**
1. **Go to GitHub** → Actions → "Generate AI Newsletter"
2. **Click "Run workflow"**
3. **❌ Leave "Production Mode" unchecked** (default)
4. **Review PR** → Merge (safe, won't auto-publish)
5. **Actions** → "Publish Newsletter"
6. **Choose environment**: `test` → Publish safely

### **🔍 Newsletter Discovery & Publishing**
1. **Go to GitHub** → Actions → "Publish Newsletter"
2. **✅ Check "Just list available newsletters"** → See all files
3. **Copy date** of newsletter you want to publish
4. **Run publish workflow again** with that specific date
5. **Choose environment**: `test` or `production`

## 📝 Recommended Workflow

### **For New Newsletters**:
```
1. Generate newsletter (creates PR)
2. Review content in PR
3. Merge PR → Automatically posts to TEST channel
4. Check test post looks good
5. Manually run publish workflow with PRODUCTION
```

### **For Regular Use**:
```
1. Wednesday morning: AI generates newsletter → Creates PR
2. You review and merge → Posts to TEST
3. You verify it looks good
4. Manually trigger PRODUCTION when ready
```

## 🔧 Setup Requirements

### **Slack Channels**
- **`#ai-publish-test`**: Your bot must be added to this channel
- **`#mitigram-ai`**: Your bot must be added to this channel

### **To Add Bot to Channels**:
1. Go to each Slack channel
2. Type: `/invite @your-bot-name`
3. Or use "Add people" and search for your bot

## 🎯 Benefits of This Setup

✅ **Safe Testing**: Never accidentally post drafts to the whole company  
✅ **Easy to Use**: Simple dropdown in GitHub Actions  
✅ **Flexible**: Can test multiple times before going live  
✅ **Rollback Safe**: Production posts are always intentional  
✅ **Beginner Friendly**: Clear separation, hard to mess up  

## 🚨 Safety Features

- **Default is TEST**: If no environment chosen, defaults to test channel
- **Clear Labels**: Workflow shows which environment it's publishing to
- **Manual Production**: Production requires intentional manual trigger

## 🔮 Future Enhancements

Later you can add:
- **Different Confluence spaces** for test vs production
- **Email notifications** for production posts
- **Approval workflows** for production
- **Scheduled production** posts (e.g., auto-publish Fridays)

## 🆘 Troubleshooting

**Bot not in channel**: Add your bot to both Slack channels  
**Wrong environment**: Check the dropdown selection in GitHub Actions  
**Missing content**: Ensure newsletter files exist before publishing  

---

*This staging system grows with you - start simple, add complexity as needed!* 🎯
