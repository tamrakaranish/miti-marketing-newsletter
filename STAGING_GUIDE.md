# 🚀 Newsletter Staging Guide

A beginner-friendly guide to using test vs production environments for your AI newsletter.

## 📋 How It Works

### **Test Environment**
- **Slack Channel**: `#ai-publish-test`
- **Purpose**: Safe testing, drafts, experiments
- **Who sees it**: Only you and selected team members

### **Production Environment**  
- **Slack Channel**: `#mitigram-ai`
- **Purpose**: Live newsletters for the whole company
- **Who sees it**: Everyone in the company

### **Confluence**: Both environments save to the same space (you can separate this later if needed)

## 🎯 How to Use

### **Option 1: Manual Publishing** (Recommended)
1. **Go to GitHub** → Actions → "Publish Newsletter"
2. **Click "Run workflow"**
3. **Choose your environment**:
   - `test` → Posts to `#ai-publish-test`
   - `production` → Posts to `#mitigram-ai`
4. **Click "Run workflow"**

### **Option 2: Automatic Publishing** (Advanced)
When newsletters are merged from PRs, they default to **test** environment.

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
