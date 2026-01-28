"""
Modal Backend - RetailRoadshow Scraper

This runs the heavy browser automation on Modal's infrastructure.
Deploy with: modal deploy modal_scraper.py

SETUP:
1. Install Modal: pip install modal
2. Authenticate: modal token new
3. Set secrets in Modal dashboard:
   - GOOGLE_CREDENTIALS_JSON (base64 encoded credentials.json)
4. Deploy: modal deploy modal_scraper.py
"""

import modal
import re
import io
import json
import base64
from typing import Optional, List

# Modal app definition
app = modal.App("roadshow-scraper")

# Image with Playwright and Google API dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "playwright",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "requests",
        "fastapi",
    )
    .run_commands("playwright install chromium && playwright install-deps")
)


def get_google_credentials():
    """Load Google credentials from Modal secret (passed via secrets decorator)."""
    import os
    from google.oauth2 import service_account
    
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_b64:
        raise ValueError(
            "GOOGLE_CREDENTIALS_JSON not found in environment. "
            "Create a secret named 'google-credentials' at: https://modal.com/secrets"
        )
    
    creds_json = base64.b64decode(creds_b64).decode()
    creds_dict = json.loads(creds_json)
    
    return service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/documents",
        ]
    )


def extract_ticker(header_text: str) -> Optional[str]:
    """Extract ticker from header using regex patterns."""
    # Primary: "(NASDAQ: AAPL)" format
    match = re.search(r"\((?:NASDAQ|NYSE|TSX|OTC):\s*([A-Z]{1,5})\)", header_text, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()
    
    # Fallback: "(TICK)" at end
    match = re.search(r"\(([A-Z]{1,5})\)$", header_text.strip(), re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()
    
    return None


@app.function(
    image=image,
    timeout=600,  # 10 minute timeout for long presentations
)
def scrape_roadshow(url: str, drive_folder_id: Optional[str] = None) -> dict:
    """
    Scrape a roadshow presentation and upload to Google Drive/Docs.
    
    Args:
        url: RetailRoadshow presentation URL
        drive_folder_id: Optional Google Drive folder ID
        
    Returns:
        Dict with result status and document/file ID
    """
    from playwright.sync_api import sync_playwright
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    import requests
    
    credentials = get_google_credentials()
    drive_service = build("drive", "v3", credentials=credentials)
    docs_service = build("docs", "v1", credentials=credentials)
    
    result = {"url": url, "status": "started"}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Bypass disclaimer modals
            # [UPDATE SELECTOR] - Adjust based on site structure
            for selector in ["button:has-text('Agree')", "button:has-text('Accept')", "button:has-text('Enter')"]:
                try:
                    btn = page.query_selector(selector)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(1000)
                        break
                except:
                    continue
            
            # Extract ticker from header
            # [UPDATE SELECTOR] - Adjust header selector
            header = page.query_selector("h1") or page.query_selector(".presentation-title")
            header_text = header.inner_text() if header else page.title()
            ticker = extract_ticker(header_text) or "UNKNOWN"
            result["ticker"] = ticker
            
            # Check for PDF download
            # [UPDATE SELECTOR] - Adjust PDF link selector
            pdf_link = page.query_selector("a:has-text('Download PDF')") or page.query_selector("a[href$='.pdf']")
            
            if pdf_link:
                pdf_url = pdf_link.get_attribute("href")
                if pdf_url:
                    if pdf_url.startswith("/"):
                        base = "/".join(url.split("/")[:3])
                        pdf_url = base + pdf_url
                    
                    # Download and upload PDF
                    resp = requests.get(pdf_url, timeout=60)
                    if resp.status_code == 200:
                        file_metadata = {"name": f"{ticker} - Roadshow.pdf", "mimeType": "application/pdf"}
                        if drive_folder_id:
                            file_metadata["parents"] = [drive_folder_id]
                        
                        media = MediaIoBaseUpload(io.BytesIO(resp.content), mimetype="application/pdf")
                        file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
                        
                        result["status"] = "success"
                        result["type"] = "pdf"
                        result["file_id"] = file.get("id")
                        return result
            
            # Scrape slide images
            # [UPDATE SELECTOR] - Adjust slide container and navigation selectors
            slides = []
            slide_selectors = [".slide-container >> img", "img.slide", ".slide-image"]
            next_selectors = ["button:has-text('Next')", "button[aria-label='Next']", ".next-slide"]
            
            def find_slide():
                for sel in slide_selectors:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        return el
                return None
            
            def find_next():
                for sel in next_selectors:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        disabled = el.get_attribute("disabled")
                        if disabled is None:
                            return el
                return None
            
            page.wait_for_timeout(2000)
            
            # Capture first slide
            slide_el = find_slide()
            if slide_el:
                slides.append(slide_el.screenshot())
            
            # Navigate and capture remaining slides
            for _ in range(500):  # Safety limit
                next_btn = find_next()
                if not next_btn:
                    break
                
                next_btn.click()
                page.wait_for_timeout(500)
                
                slide_el = find_slide()
                if slide_el:
                    img = slide_el.screenshot()
                    if slides and img == slides[-1]:
                        break  # End of deck
                    slides.append(img)
            
            if not slides:
                result["status"] = "error"
                result["error"] = "No slides captured"
                return result
            
            # Create Google Doc with slides
            doc = docs_service.documents().create(body={"title": f"{ticker} - Roadshow"}).execute()
            doc_id = doc.get("documentId")
            
            if drive_folder_id:
                drive_service.files().update(fileId=doc_id, addParents=drive_folder_id, fields="id").execute()
            
            # Upload images and insert into doc
            requests_list = []
            index = 1
            
            for i, slide_data in enumerate(slides):
                # Upload image
                img_meta = {"name": f"slide_{i+1}.png"}
                media = MediaIoBaseUpload(io.BytesIO(slide_data), mimetype="image/png")
                img_file = drive_service.files().create(body=img_meta, media_body=media, fields="id").execute()
                drive_service.permissions().create(fileId=img_file.get("id"), body={"type": "anyone", "role": "reader"}).execute()
                
                img_url = f"https://drive.google.com/uc?id={img_file.get('id')}"
                
                requests_list.append({"insertText": {"location": {"index": index}, "text": f"Slide {i+1}\n"}})
                index += len(f"Slide {i+1}\n")
                
                requests_list.append({
                    "insertInlineImage": {
                        "location": {"index": index},
                        "uri": img_url,
                        "objectSize": {"width": {"magnitude": 500, "unit": "PT"}, "height": {"magnitude": 375, "unit": "PT"}}
                    }
                })
                index += 1
                
                requests_list.append({"insertText": {"location": {"index": index}, "text": "\n\n"}})
                index += 2
            
            if requests_list:
                docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests_list}).execute()
            
            result["status"] = "success"
            result["type"] = "doc"
            result["doc_id"] = doc_id
            result["slides_count"] = len(slides)
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        finally:
            browser.close()
    
    return result


@app.function(image=image)
@modal.web_endpoint(method="POST")
def webhook(data: dict) -> dict:
    """
    Webhook endpoint for triggering scrapes from Vercel.
    
    Expected payload:
    {
        "url": "https://retailroadshow.com/...",
        "drive_folder_id": "optional-folder-id"
    }
    """
    url = data.get("url")
    if not url:
        return {"error": "Missing 'url' in request"}
    
    # Spawn async job
    job = scrape_roadshow.spawn(url, data.get("drive_folder_id"))
    
    return {
        "status": "queued",
        "job_id": job.object_id,
        "url": url
    }


@app.function(image=image)
@modal.web_endpoint(method="GET")
def status(job_id: str) -> dict:
    """Check status of a scrape job."""
    try:
        from modal.functions import FunctionCall
        call = FunctionCall.from_id(job_id)
        
        try:
            result = call.get(timeout=0)
            return {"status": "completed", "result": result}
        except TimeoutError:
            return {"status": "running", "job_id": job_id}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}
