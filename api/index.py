"""
Vercel Serverless API - Scrape Trigger Endpoint

This lightweight API receives scrape requests and triggers the Modal backend
for heavy browser automation work.
"""

import os
import json
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "service": "RetailRoadshow Scraper API",
            "endpoints": {
                "POST /api": "Trigger scrape job",
                "GET /api": "Health check"
            }
        }).encode())

    def do_POST(self):
        """Trigger a scrape job via Modal backend."""
        try:
            # Parse request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            url = data.get("url")
            if not url:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing 'url' in request body"
                }).encode())
                return

            # Get Modal webhook URL from environment
            modal_webhook = os.environ.get("MODAL_WEBHOOK_URL")
            
            if not modal_webhook:
                # If no Modal backend configured, return instructions
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Modal backend not configured",
                    "setup": "Set MODAL_WEBHOOK_URL environment variable in Vercel"
                }).encode())
                return

            # Trigger Modal scraper with user's access token and email
            payload = json.dumps({
                "url": url,
                "drive_folder_id": data.get("drive_folder_id"),
                "access_token": data.get("access_token"),  # User's Google OAuth token
                "user_email": data.get("user_email")  # User's email for notification
            }).encode()

            req = urllib.request.Request(
                modal_webhook,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())

            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "accepted",
                "message": "Scrape job triggered",
                "job": result
            }).encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Invalid JSON in request body"
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": str(e)
            }).encode())
