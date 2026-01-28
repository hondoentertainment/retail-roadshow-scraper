---
description: Deploy the Modal backend for the scraper
---
# Deploy Modal Backend

// turbo-all

1. Ensure Modal CLI is available:
```powershell
& "C:\Users\kyle\AppData\Local\Programs\Python\Python311\Scripts\modal.exe" --version
```

2. Authenticate with Modal (if needed):
```powershell
& "C:\Users\kyle\AppData\Local\Programs\Python\Python311\Scripts\modal.exe" token new
```

3. Deploy the scraper:
```powershell
& "C:\Users\kyle\AppData\Local\Programs\Python\Python311\Scripts\modal.exe" deploy modal_scraper.py
```

4. Note the webhook URL from the output (format: `https://hondoentertainment--roadshow-scraper-webhook.modal.run`)

5. If the webhook URL changed, update it in Vercel environment variables
