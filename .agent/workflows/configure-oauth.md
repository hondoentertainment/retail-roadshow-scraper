---
description: Configure Google OAuth for the application
---
# Configure Google OAuth

## OAuth Client Setup

1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)

2. Create or select an OAuth 2.0 Client ID (Web application)

3. Add **Authorized JavaScript origins**:
   - `https://retail-roadshow-scraper.vercel.app`
   - `http://localhost:3000` (for local testing)

4. Save changes

## OAuth Consent Screen

1. Go to [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)

2. Configure scopes - add these if not present:
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/gmail.send`

3. Add test users (while in Testing mode):
   - Add your email address to test the app

## Update Client ID in Code

If the Client ID changes, update it in:
- `index.html` line 364
- `public/index.html` line 364

```javascript
const GOOGLE_CLIENT_ID = 'YOUR_CLIENT_ID.apps.googleusercontent.com';
```
