---
description: Full deployment of both Modal and Vercel
---
# Full Deployment

// turbo-all

Deploy both the Modal backend and Vercel frontend.

## 1. Deploy Modal Backend

```powershell
& "C:\Users\kyle\AppData\Local\Programs\Python\Python311\Scripts\modal.exe" deploy modal_scraper.py
```

## 2. Commit and Deploy to Vercel

```powershell
git add .
```

```powershell
git commit -m "Deploy updates"
```

```powershell
npx vercel --prod
```

## 3. Verify

- Frontend: https://retail-roadshow-scraper.vercel.app/
- API Health: https://retail-roadshow-scraper.vercel.app/api
