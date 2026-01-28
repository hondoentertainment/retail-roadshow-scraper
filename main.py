"""
RetailRoadshow Slide Deck Scraper & Google Docs Compiler

This script automates:
1. Navigating to a roadshow presentation URL
2. Bypassing disclaimer modals
3. Extracting the ticker symbol from the page header
4. Scraping slide images (handling Shadow DOM) or downloading PDF
5. Uploading to Google Drive or creating a Google Doc with embedded images

IMPORTANT: CSS selectors marked with # [UPDATE SELECTOR] comments will likely
need adjustment based on the target site's live structure.
"""

import re
import io
import requests
from typing import Optional, List, Tuple

from playwright.sync_api import sync_playwright, Page, ElementHandle
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload


# =============================================================================
# CONFIGURATION
# =============================================================================

# Path to your Google Cloud service account credentials JSON file
CREDENTIALS_FILE = "credentials.json"

# Google API scopes required for Drive and Docs access
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

# Target URL - set this to the roadshow presentation URL
TARGET_URL = "https://www.retailroadshow.com/example-presentation"

# Optional: Google Drive folder ID to upload files to (leave None for root)
DRIVE_FOLDER_ID: Optional[str] = None


# =============================================================================
# GOOGLE API AUTHENTICATION
# =============================================================================

def get_google_credentials():
    """
    Authenticate using service account credentials.
    
    Returns:
        google.oauth2.service_account.Credentials: Authenticated credentials
    """
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )
    return credentials


def get_drive_service():
    """Build and return the Google Drive API service."""
    credentials = get_google_credentials()
    return build("drive", "v3", credentials=credentials)


def get_docs_service():
    """Build and return the Google Docs API service."""
    credentials = get_google_credentials()
    return build("docs", "v1", credentials=credentials)


# =============================================================================
# TICKER EXTRACTION
# =============================================================================

def extract_ticker(header_text: str) -> Optional[str]:
    """
    Extract the stock ticker symbol from the page header text.
    
    Uses two regex patterns:
    1. Primary: Matches "(NASDAQ: TICK)" or "(NYSE: TICK)" format
    2. Fallback: Matches "(TICK)" at end of string
    
    Args:
        header_text: The header text to search for ticker
        
    Returns:
        The extracted ticker symbol (uppercase, stripped) or None
    """
    # Primary regex: Match exchange-prefixed tickers
    # Example matches: "(NASDAQ: AAPL)", "(NYSE: IBM)", "(TSX: SHOP)", "(OTC: PNKF)"
    primary_pattern = r"\((?:NASDAQ|NYSE|TSX|OTC):\s*([A-Z]{1,5})\)"
    match = re.search(primary_pattern, header_text, re.IGNORECASE)
    
    if match:
        return match.group(1).strip().upper()
    
    # Fallback regex: Match simple ticker at end of header
    # Example matches: "Company Name (TICK)"
    fallback_pattern = r"\(([A-Z]{1,5})\)$"
    match = re.search(fallback_pattern, header_text.strip(), re.IGNORECASE)
    
    if match:
        return match.group(1).strip().upper()
    
    return None


# =============================================================================
# BROWSER AUTOMATION
# =============================================================================

def bypass_disclaimer_modal(page: Page) -> bool:
    """
    Detect and click through disclaimer/terms modals.
    
    Returns:
        True if a modal was found and clicked, False otherwise
    """
    # Common button selectors for disclaimer modals
    # [UPDATE SELECTOR] - These selectors may need adjustment based on the site
    disclaimer_selectors = [
        "button:has-text('Agree')",
        "button:has-text('Accept')",
        "button:has-text('Enter')",
        "button:has-text('I Agree')",
        "button:has-text('Continue')",
        "button.agree",           # [UPDATE SELECTOR] - Class-based selector
        "button.accept",          # [UPDATE SELECTOR] - Class-based selector
        "[data-testid='agree']",  # [UPDATE SELECTOR] - Data attribute selector
        "#agree-button",          # [UPDATE SELECTOR] - ID-based selector
        ".modal-accept",          # [UPDATE SELECTOR] - Modal accept button
    ]
    
    for selector in disclaimer_selectors:
        try:
            button = page.query_selector(selector)
            if button and button.is_visible():
                button.click()
                page.wait_for_timeout(1000)  # Wait for modal to close
                print(f"Clicked disclaimer button: {selector}")
                return True
        except Exception:
            continue
    
    return False


def get_header_text(page: Page) -> str:
    """
    Extract the page header text containing the company name and ticker.
    
    Returns:
        The header text, or empty string if not found
    """
    # [UPDATE SELECTOR] - Header selector may vary by page structure
    header_selectors = [
        "h1",
        ".presentation-title",     # [UPDATE SELECTOR]
        ".company-header",         # [UPDATE SELECTOR]
        "[data-testid='header']",  # [UPDATE SELECTOR]
        ".roadshow-title",         # [UPDATE SELECTOR]
        "header h1",
        ".title-container h1",     # [UPDATE SELECTOR]
    ]
    
    for selector in header_selectors:
        try:
            element = page.query_selector(selector)
            if element:
                text = element.inner_text()
                if text and len(text) > 5:  # Basic validation
                    return text.strip()
        except Exception:
            continue
    
    # Fallback: try to get title from page
    return page.title()


def pierce_shadow_dom(page: Page, selector: str) -> Optional[ElementHandle]:
    """
    Query selector that pierces through Shadow DOM boundaries.
    
    Playwright's >> syntax allows piercing shadow roots.
    
    Args:
        page: Playwright page object
        selector: CSS selector (use >> for shadow-piercing)
        
    Returns:
        ElementHandle if found, None otherwise
    """
    try:
        # Playwright's >> css engine pierces shadow DOM
        # Example: "div.container >> button.next"
        return page.query_selector(selector)
    except Exception:
        return None


def check_for_pdf_download(page: Page) -> Optional[str]:
    """
    Check if a PDF download button/link exists and return the PDF URL.
    
    Returns:
        PDF download URL if found, None otherwise
    """
    # [UPDATE SELECTOR] - PDF download button selectors
    pdf_selectors = [
        "a:has-text('Download PDF')",
        "button:has-text('Download PDF')",
        "a[href$='.pdf']",
        ".download-pdf",           # [UPDATE SELECTOR]
        "[data-action='download']", # [UPDATE SELECTOR]
        "a.pdf-download",          # [UPDATE SELECTOR]
    ]
    
    for selector in pdf_selectors:
        try:
            element = page.query_selector(selector)
            if element:
                href = element.get_attribute("href")
                if href:
                    # Handle relative URLs
                    if href.startswith("/"):
                        base_url = page.url.split("/")[0:3]
                        href = "/".join(base_url) + href
                    return href
                    
                # If it's a button, try clicking and intercepting download
                # For now, return a marker that PDF exists
                return "PDF_BUTTON_EXISTS"
        except Exception:
            continue
    
    return None


def scrape_slide_images(page: Page) -> List[bytes]:
    """
    Scrape slide images from the presentation viewer.
    
    Handles Shadow DOM by using Playwright's shadow-piercing selectors.
    Iterates through slides using the "Next" button.
    
    Returns:
        List of image data as bytes (screenshots or downloaded images)
    """
    slides: List[bytes] = []
    slide_count = 0
    max_slides = 500  # Safety limit
    
    # [UPDATE SELECTOR] - These selectors target the slide viewer components
    # Shadow-piercing syntax: "outer-element >> inner-element"
    
    # Slide container selectors (may be inside shadow DOM)
    slide_container_selectors = [
        ".slide-container >> img",           # [UPDATE SELECTOR]
        ".slide-viewer >> .slide-image",     # [UPDATE SELECTOR]
        "#presentation-viewer >> img",       # [UPDATE SELECTOR]
        ".viewer-component >> canvas",       # [UPDATE SELECTOR]
        "[data-slide-viewer] >> img",        # [UPDATE SELECTOR]
        ".slide-canvas",                     # [UPDATE SELECTOR]
        "img.slide",                         # [UPDATE SELECTOR]
    ]
    
    # Next button selectors (may be inside shadow DOM)
    next_button_selectors = [
        ".slide-nav >> button.next",         # [UPDATE SELECTOR]
        "button:has-text('Next')",
        "button[aria-label='Next']",
        ".next-slide",                       # [UPDATE SELECTOR]
        "[data-action='next']",              # [UPDATE SELECTOR]
        ".viewer >> .nav-next",              # [UPDATE SELECTOR]
        "button.arrow-right",                # [UPDATE SELECTOR]
    ]
    
    def find_slide_element() -> Optional[ElementHandle]:
        """Find the current slide image/canvas element."""
        for selector in slide_container_selectors:
            element = pierce_shadow_dom(page, selector)
            if element and element.is_visible():
                return element
        return None
    
    def find_next_button() -> Optional[ElementHandle]:
        """Find the next slide navigation button."""
        for selector in next_button_selectors:
            element = pierce_shadow_dom(page, selector)
            if element and element.is_visible():
                # Check if button is enabled
                disabled = element.get_attribute("disabled")
                aria_disabled = element.get_attribute("aria-disabled")
                if disabled is None and aria_disabled != "true":
                    return element
        return None
    
    def capture_slide(element: ElementHandle) -> bytes:
        """Capture slide as screenshot or download image."""
        # Try to get image source first
        tag_name = element.evaluate("el => el.tagName.toLowerCase()")
        
        if tag_name == "img":
            src = element.get_attribute("src")
            if src and src.startswith("http"):
                try:
                    response = requests.get(src, timeout=30)
                    if response.status_code == 200:
                        return response.content
                except Exception:
                    pass
        
        # Fallback: take screenshot of element
        return element.screenshot()
    
    # Wait for viewer to load
    page.wait_for_timeout(2000)
    
    # Capture initial slide
    slide_element = find_slide_element()
    if slide_element:
        slides.append(capture_slide(slide_element))
        slide_count += 1
        print(f"Captured slide {slide_count}")
    
    # Iterate through remaining slides
    while slide_count < max_slides:
        next_button = find_next_button()
        
        if not next_button:
            print("No more slides (next button not found or disabled)")
            break
        
        try:
            next_button.click()
            page.wait_for_timeout(500)  # Wait for slide transition
            
            # Capture new slide
            slide_element = find_slide_element()
            if slide_element:
                slide_data = capture_slide(slide_element)
                
                # Check for duplicate (end of deck often loops)
                if slides and slide_data == slides[-1]:
                    print("Duplicate slide detected, ending capture")
                    break
                
                slides.append(slide_data)
                slide_count += 1
                print(f"Captured slide {slide_count}")
            else:
                print("Could not find slide element after navigation")
                break
                
        except Exception as e:
            print(f"Error navigating to next slide: {e}")
            break
    
    return slides


# =============================================================================
# GOOGLE DRIVE/DOCS OPERATIONS
# =============================================================================

def upload_pdf_to_drive(ticker: str, pdf_data: bytes) -> str:
    """
    Upload a PDF file to Google Drive.
    
    Args:
        ticker: Stock ticker symbol for naming
        pdf_data: PDF file contents as bytes
        
    Returns:
        The ID of the uploaded file
    """
    drive_service = get_drive_service()
    
    file_name = f"{ticker} - Roadshow.pdf"
    
    file_metadata = {
        "name": file_name,
        "mimeType": "application/pdf",
    }
    
    if DRIVE_FOLDER_ID:
        file_metadata["parents"] = [DRIVE_FOLDER_ID]
    
    media = MediaIoBaseUpload(
        io.BytesIO(pdf_data),
        mimetype="application/pdf",
        resumable=True
    )
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    
    print(f"Uploaded PDF to Drive: {file_name} (ID: {file.get('id')})")
    return file.get("id")


def upload_image_to_drive(image_data: bytes, index: int) -> str:
    """
    Upload an image to Google Drive for embedding in Docs.
    
    Args:
        image_data: Image file contents as bytes
        index: Slide index for naming
        
    Returns:
        The ID of the uploaded file
    """
    drive_service = get_drive_service()
    
    file_metadata = {
        "name": f"slide_{index}.png",
    }
    
    if DRIVE_FOLDER_ID:
        file_metadata["parents"] = [DRIVE_FOLDER_ID]
    
    media = MediaIoBaseUpload(
        io.BytesIO(image_data),
        mimetype="image/png",
        resumable=True
    )
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    
    # Make the file publicly accessible for embedding
    drive_service.permissions().create(
        fileId=file.get("id"),
        body={"type": "anyone", "role": "reader"}
    ).execute()
    
    return file.get("id")


def create_google_doc_with_images(ticker: str, slides: List[bytes]) -> str:
    """
    Create a Google Doc and append slide images sequentially.
    
    Args:
        ticker: Stock ticker symbol for document title
        slides: List of slide image data as bytes
        
    Returns:
        The ID of the created document
    """
    drive_service = get_drive_service()
    docs_service = get_docs_service()
    
    doc_title = f"{ticker} - Roadshow"
    
    # Create new document
    doc = docs_service.documents().create(
        body={"title": doc_title}
    ).execute()
    
    doc_id = doc.get("documentId")
    print(f"Created Google Doc: {doc_title} (ID: {doc_id})")
    
    # Move to folder if specified
    if DRIVE_FOLDER_ID:
        drive_service.files().update(
            fileId=doc_id,
            addParents=DRIVE_FOLDER_ID,
            fields="id, parents"
        ).execute()
    
    # Upload images and build insert requests
    requests_list = []
    current_index = 1  # Document index starts at 1
    
    for i, slide_data in enumerate(slides):
        # Upload image to Drive
        image_id = upload_image_to_drive(slide_data, i + 1)
        image_url = f"https://drive.google.com/uc?id={image_id}"
        
        # Add slide number header
        requests_list.append({
            "insertText": {
                "location": {"index": current_index},
                "text": f"Slide {i + 1}\n"
            }
        })
        current_index += len(f"Slide {i + 1}\n")
        
        # Insert image
        requests_list.append({
            "insertInlineImage": {
                "location": {"index": current_index},
                "uri": image_url,
                "objectSize": {
                    "width": {"magnitude": 500, "unit": "PT"},
                    "height": {"magnitude": 375, "unit": "PT"}  # 4:3 aspect ratio
                }
            }
        })
        current_index += 1  # Image takes 1 index unit
        
        # Add spacing between slides
        requests_list.append({
            "insertText": {
                "location": {"index": current_index},
                "text": "\n\n"
            }
        })
        current_index += 2
        
        print(f"Added slide {i + 1} to document")
    
    # Execute batch update
    if requests_list:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests_list}
        ).execute()
    
    print(f"Document complete with {len(slides)} slides")
    return doc_id


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main(url: str = TARGET_URL):
    """
    Main execution flow for scraping and uploading roadshow content.
    
    Args:
        url: The target roadshow presentation URL
    """
    print(f"Starting scrape of: {url}")
    
    with sync_playwright() as p:
        # Launch headless Chromium browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate to target URL
            page.goto(url, wait_until="networkidle", timeout=60000)
            print("Page loaded successfully")
            
            # Handle disclaimer modal
            if bypass_disclaimer_modal(page):
                print("Bypassed disclaimer modal")
                page.wait_for_timeout(1000)
            
            # Extract ticker from header
            header_text = get_header_text(page)
            print(f"Header text: {header_text}")
            
            ticker = extract_ticker(header_text)
            if not ticker:
                print("WARNING: Could not extract ticker, using 'UNKNOWN'")
                ticker = "UNKNOWN"
            else:
                print(f"Extracted ticker: {ticker}")
            
            # Check for PDF download first
            pdf_url = check_for_pdf_download(page)
            
            if pdf_url and pdf_url != "PDF_BUTTON_EXISTS":
                # Scenario A: PDF download available
                print(f"Found PDF download: {pdf_url}")
                
                response = requests.get(pdf_url, timeout=60)
                if response.status_code == 200:
                    pdf_data = response.content
                    upload_pdf_to_drive(ticker, pdf_data)
                    print("PDF uploaded successfully!")
                else:
                    print(f"Failed to download PDF: {response.status_code}")
                    
            else:
                # Scenario B: Scrape slide images
                print("No PDF found, scraping slide images...")
                
                slides = scrape_slide_images(page)
                
                if slides:
                    print(f"Captured {len(slides)} slides")
                    create_google_doc_with_images(ticker, slides)
                    print("Google Doc created successfully!")
                else:
                    print("ERROR: No slides could be captured")
                    
        except Exception as e:
            print(f"Error during scraping: {e}")
            raise
            
        finally:
            browser.close()
            print("Browser closed")


if __name__ == "__main__":
    # You can modify TARGET_URL above or pass a URL directly here
    main()
