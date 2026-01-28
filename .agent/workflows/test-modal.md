---
description: Test the Modal scraper locally
---
# Test Modal Locally

Run the Modal scraper function locally for testing.

## Prerequisites
- Modal CLI authenticated
- Python 3.11 with modal installed

## Run Local Test

```powershell
& "C:\Users\kyle\AppData\Local\Programs\Python\Python311\Scripts\modal.exe" run modal_scraper.py::scrape_roadshow --url "https://retailroadshow.com/example"
```

## Test with Access Token

For full testing with Google Drive integration, you'll need a valid OAuth access token:

```powershell
& "C:\Users\kyle\AppData\Local\Programs\Python\Python311\Scripts\modal.exe" run modal_scraper.py::scrape_roadshow --url "URL" --access-token "TOKEN"
```

## Check Logs

View recent logs in Modal dashboard: https://modal.com/apps
