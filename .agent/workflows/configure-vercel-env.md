---
description: Set up Vercel environment variables
---
# Configure Vercel Environment Variables

## Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MODAL_WEBHOOK_URL` | Modal webhook endpoint | `https://hondoentertainment--roadshow-scraper-webhook.modal.run` |

## Setting via CLI

```powershell
npx vercel env add MODAL_WEBHOOK_URL
```

Enter the Modal webhook URL when prompted.

## Setting via Dashboard

1. Go to [Vercel Project Settings](https://vercel.com/hondo4185-5820s-projects/retail-roadshow-scraper/settings/environment-variables)

2. Add variable:
   - Name: `MODAL_WEBHOOK_URL`
   - Value: Your Modal webhook URL
   - Environments: Check all (Production, Preview, Development)

3. Click Save

4. Redeploy for changes to take effect:
```powershell
npx vercel --prod
```
