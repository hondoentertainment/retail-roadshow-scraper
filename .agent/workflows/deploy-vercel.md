---
description: Deploy the Vercel frontend and API
---
# Deploy to Vercel

// turbo-all

1. Stage all changes:
```powershell
git add .
```

2. Commit changes:
```powershell
git commit -m "Update deployment"
```

3. Deploy to production:
```powershell
npx vercel --prod
```

4. Verify the deployment at: https://retail-roadshow-scraper.vercel.app/
