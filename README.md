# RetailRoadshow Scraper

Automation agent that scrapes slide decks from RetailRoadshow presentations and compiles them into Google Docs or uploads PDFs to Google Drive.

## Features

- **Browser Automation**: Playwright-based headless Chromium scraping
- **Disclaimer Bypass**: Auto-clicks "Agree/Accept/Enter" modals
- **Ticker Extraction**: Regex-based extraction from page headers
- **Shadow DOM Support**: Pierces shadow roots for slide navigation
- **PDF Priority**: Downloads PDF if available, otherwise scrapes slides
- **Google Integration**: Uploads to Drive or creates Docs with embedded images

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Google Cloud Configuration

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Google Drive API** and **Google Docs API**
3. Create a service account and download the JSON key
4. Save as `credentials.json` in the project root
5. Share the destination Drive folder with the service account email

### 3. Configure the Script

Edit `main.py`:
- Set `TARGET_URL` to your roadshow presentation URL
- Optionally set `DRIVE_FOLDER_ID` for a specific destination folder

## Usage

```bash
python main.py
```

## Customization

CSS selectors marked with `# [UPDATE SELECTOR]` comments may need adjustment based on the target site's live structure. Key areas:

- Disclaimer buttons (lines ~95-105)
- Header selectors (lines ~115-125)
- Slide container (lines ~185-195)
- Next button (lines ~198-208)
- PDF download (lines ~155-165)

## License

MIT
