# CatchQuery Deployment Guide

## Quick Start: Deploying to Streamlit Community Cloud (FREE)

This guide will walk you through deploying your CatchQuery tool to the web for free using Streamlit Community Cloud. It will be accessible at a free `.streamlit.app` URL with password protection.

**Total Time: ~30 minutes**
**Cost: £0/month (completely free!)**
**Technical Level: Beginner-friendly**

---

## Prerequisites

Before you begin, you'll need:

1. A GitHub account (free) - Sign up at https://github.com
2. Your OpenRouter API key (already configured in `.env`)
3. A chosen password for app access

---

## Step 1: Create a GitHub Repository (15 minutes)

### 1.1 Create New Repository

1. Go to https://github.com and sign in
2. Click the green "New" button (or go to https://github.com/new)
3. Fill in the repository details:
   - **Repository name:** `catchquery` (or your preferred name)
   - **Description:** "Natural language interface for UK fish landing statistics"
   - **Visibility:** Choose "Private" (recommended) or "Public"
   - **DO NOT** initialize with README, .gitignore, or license (we have these already)
4. Click "Create repository"

### 1.2 Push Your Code to GitHub

Open Terminal and navigate to your project folder, then run these commands:

```bash
# Navigate to your project directory
cd "/Users/willdavies/Library/Mobile Documents/com~apple~CloudDocs/claude_code_main_folder/coding_projects/landings_tool"

# Initialize git (if not already done)
git init

# Add all files to git
git add .

# Create first commit
git commit -m "Initial commit: CatchQuery with password authentication"

# Connect to GitHub (replace USERNAME and REPO with your values)
git remote add origin https://github.com/USERNAME/REPO.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Note:** If prompted for credentials, use your GitHub username and a Personal Access Token (not your password). Create a token at: https://github.com/settings/tokens

### 1.3 Verify Upload

1. Refresh your GitHub repository page
2. You should see all your files, including:
   - `app.py`
   - `mmo_landings.db` (227MB - this might take a few minutes to upload)
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `chart_generator.py`
3. **Important:** Check that `.env` is NOT visible (it should be hidden by `.gitignore`)

---

## Step 2: Deploy to Streamlit Cloud (10 minutes)

### 2.1 Create Streamlit Account

1. Go to https://share.streamlit.io/
2. Click "Sign in" in the top right
3. Choose "Continue with GitHub"
4. Authorize Streamlit to access your GitHub account

### 2.2 Deploy Your App

1. Once signed in, click "New app" button
2. Fill in the deployment settings:
   - **Repository:** Select your `catchquery` repository from the dropdown
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** Choose a custom URL (e.g., `yourname-catchquery`) or leave default
3. Click "Deploy!"

### 2.3 Wait for Deployment

- Streamlit will now build and deploy your app
- This takes 2-5 minutes
- You'll see a progress indicator with build logs
- Once complete, your app will be live!

### 2.4 Initial Test

1. Once deployed, click "View app" or visit the URL provided
2. You should see: "APP_PASSWORD not configured" error - this is expected!
3. We'll fix this in the next step by adding secrets

---

## Step 3: Configure Secrets (5 minutes)

### 3.1 Access App Settings

1. In the Streamlit Cloud dashboard, find your app
2. Click the "..." menu next to your app name
3. Select "Settings"

### 3.2 Add Secrets

1. In the settings menu, click "Secrets" in the left sidebar
2. You'll see a text editor where you can add secrets in TOML format
3. Copy and paste this (replace with your actual values):

```toml
# OpenRouter API Key
OPENROUTER_API_KEY = "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"

# Application Password (choose a strong password)
APP_PASSWORD = "your-secure-password-here"
```

4. Replace `"your-secure-password-here"` with your chosen password (e.g., `"MarineData2024!"`)
5. Click "Save"

### 3.3 Test Authentication

1. Go back to your app (click "View app" or refresh the browser)
2. You should now see the password prompt: "CatchQuery UK - Access Required"
3. Enter the password you just configured
4. If correct, you'll see the full CatchQuery interface
5. If incorrect, you'll see "Password incorrect. Please try again."

---

## Step 4: Share with Colleagues (2 minutes)

### 4.1 Find Your App URL

1. In Streamlit Cloud, go to your app dashboard
2. Your app URL will be something like: `https://yourname-catchquery.streamlit.app`
3. Copy this URL - you'll share it with colleagues

### 4.2 Prepare Access Instructions

Send your colleagues an email with:

```
Subject: Access to CatchQuery - UK Fish Landings Tool

Hi team,

I've set up CatchQuery, a natural language tool for querying UK fish landing data (MMO statistics, 2024).

Access details:
- URL: https://yourname-catchquery.streamlit.app
- Password: [your-password-here]

How to use:
1. Visit the URL and enter the password
2. Type questions in plain English (e.g., "Which port landed the most mackerel in 2024?")
3. The tool will generate charts and data tables automatically
4. You can download results as CSV

Example queries:
- "Top 10 species by value in 2024"
- "Show me mackerel landings in Scotland by month"
- "Compare shellfish landings between England and Scotland"

Note: The first load may take 30 seconds if the app has been idle.

Let me know if you have any issues accessing the tool!
```

---

## Testing Checklist

After deployment, verify these features work:

- [ ] Password prompt appears on first visit
- [ ] Incorrect password shows error message
- [ ] Correct password grants access to full app
- [ ] Can enter natural language queries
- [ ] SQL queries are generated correctly
- [ ] Results display in tables
- [ ] Charts are generated automatically
- [ ] CSV export works
- [ ] App loads at your `.streamlit.app` URL
- [ ] HTTPS is enabled (green padlock in browser)

---

## Maintenance & Updates

### Updating the App

When you make changes to your code:

1. Make changes locally
2. Test thoroughly with `streamlit run app.py`
3. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```
4. Streamlit Cloud will automatically detect the changes and redeploy (takes ~2 minutes)

### Changing the Password

1. Go to Streamlit Cloud → Your app → Settings → Secrets
2. Update the `APP_PASSWORD` value
3. Click "Save"
4. Changes take effect immediately (no need to redeploy)
5. Notify your colleagues of the new password

### Monitoring Usage

1. In Streamlit Cloud, go to your app dashboard
2. Click "Analytics" to see:
   - Number of visitors
   - Active users
   - Resource usage
3. Check OpenRouter dashboard for API usage and costs: https://openrouter.ai/activity

### Checking Costs

- **Streamlit hosting:** £0/month (free tier)
- **OpenRouter API:** Check at https://openrouter.ai/activity
  - Expected: ~£0.001-0.002 per query
  - For 50 queries/month: ~£0.10/month
  - For 200 queries/month: ~£0.40/month

---

## Troubleshooting

### "APP_PASSWORD not configured" error
- **Solution:** Add `APP_PASSWORD` to Streamlit Cloud secrets (see Step 3)

### "Missing API Key" error
- **Solution:** Add `OPENROUTER_API_KEY` to Streamlit Cloud secrets (see Step 3)

### App is slow or times out
- **Cause:** App "sleeps" after 5-10 minutes of inactivity (free tier limitation)
- **Solution:** First load takes 30 seconds to wake up - this is normal

### Database errors
- **Cause:** Database file didn't upload to GitHub (too large)
- **Solution:** Check GitHub repo - `mmo_landings.db` should be 227MB. If missing:
  1. Check `.gitignore` doesn't exclude `.db` files
  2. Use `git lfs` (Large File Storage) for files over 100MB
  3. Or host database separately (Dropbox, S3) and download on app startup

### Charts not displaying
- **Cause:** `chart_generator.py` not found or import error
- **Solution:** Ensure `chart_generator.py` is in GitHub repo alongside `app.py`

### Password accepted but app crashes
- **Cause:** Missing dependencies or database connection issue
- **Solution:** Check Streamlit Cloud logs (Settings → Logs) for error details

---

## Advanced Options (Optional)

### Using Git LFS for Large Database

If GitHub complains about the 227MB database file:

```bash
# Install Git LFS
brew install git-lfs  # macOS
# or: sudo apt-get install git-lfs  # Linux

# Initialize Git LFS
git lfs install

# Track the database file
git lfs track "*.db"

# Add and commit
git add .gitattributes
git add mmo_landings.db
git commit -m "Add database with Git LFS"
git push
```

### Setting Up GitHub Actions for Automated Testing

Create `.github/workflows/test.yml` to run tests before deployment (advanced users only).

---

## Support & Resources

- **Streamlit Documentation:** https://docs.streamlit.io/
- **Streamlit Community Cloud:** https://docs.streamlit.io/streamlit-community-cloud
- **OpenRouter API:** https://openrouter.ai/docs
- **Git Tutorial:** https://www.atlassian.com/git/tutorials
- **GitHub Help:** https://docs.github.com/

---

## Summary

Congratulations! Your CatchQuery tool is now:

- Hosted on the web for free at your `.streamlit.app` URL
- Protected with a password
- Accessible to colleagues via a simple link
- Ready to use immediately
- Automatically backed up on GitHub

The combination of Streamlit Cloud (free hosting) + GitHub (version control) + password authentication makes this a professional and cost-effective solution for your team.

**Next Steps:**
1. Share your `.streamlit.app` URL and password with colleagues
2. Monitor usage and costs in first few weeks
3. Gather feedback on additional features
4. Consider adding more years of MMO data if needed

**Optional Future Enhancement:**
If you'd like a custom domain (e.g., `catchquery.adaptmel.org`) instead of the `.streamlit.app` URL, you can add one later through Streamlit Cloud settings and configure a CNAME record with your domain registrar. But the free `.streamlit.app` URL works perfectly well!

Enjoy using CatchQuery!
