# RetailRoadshow Scraper

Automation agent that scrapes slide decks from RetailRoadshow presentations and compiles them into Google Docs or uploads PDFs to Google Drive.

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Vercel API     │ ──▶  │  Modal Backend  │ ──▶  │  Google Drive   │
│  (Trigger)      │      │  (Playwright)   │      │  / Docs         │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

- **Vercel**: Lightweight API endpoint to trigger scrapes
- **Modal**: Runs Playwright browser automation (10-min timeout)
- **Google**: Stores PDFs or creates Docs with embedded slides

## Quick Start

### 1. Deploy Modal Backend

```bash
pip install modal
modal token new
modal deploy modal_scraper.py
```

Copy the webhook URL from Modal dashboard.

### 2. Deploy Vercel Frontend

```bash
npm i -g vercel
vercel
```

Set environment variable in Vercel dashboard:
- `MODAL_WEBHOOK_URL` = your Modal webhook URL

### 3. Configure Google Credentials

In Modal dashboard, create a secret named `google-credentials`:
- `GOOGLE_CREDENTIALS_JSON` = base64-encoded credentials.json

```bash
base64 -i credentials.json
```

## API Usage

**Trigger a scrape:**
```bash
curl -X POST https://your-app.vercel.app/api \
  -H "Content-Type: application/json" \
  -d '{"url": "https://retailroadshow.com/presentation/..."}'
```

**Response:**
```json
{
  "status": "accepted",
  "job": {"status": "queued", "job_id": "..."}
}
```

## Local Development

Run the standalone script directly:
```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

## License

MIT
