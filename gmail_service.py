"""
Gmail service for reading user emails using Google API.
"""

import os
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
import base64


class GmailService:
    """Service for interacting with Gmail API."""

    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        """Initialize Gmail service with user tokens."""
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        )

        self.service = build("gmail", "v1", credentials=self.credentials)

    def get_emails(
        self, query: str = "", max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch emails based on query."""
        try:
            # Search for messages
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            # Get full message details
            for message in messages:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message["id"])
                    .execute()
                )

                # Extract email data
                headers = msg["payload"].get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"),
                    "No Subject",
                )
                sender = next(
                    (h["value"] for h in headers if h["name"] == "From"),
                    "Unknown Sender",
                )
                date = next(
                    (h["value"] for h in headers if h["name"] == "Date"), ""
                )

                # Get email body
                body = self._extract_body(msg["payload"])

                emails.append(
                    {
                        "id": msg["id"],
                        "subject": subject,
                        "sender": sender,
                        "date": date,
                        "body": body,
                        "snippet": msg.get("snippet", ""),
                    }
                )

            return emails

        except HttpError as e:
            raise HTTPException(
                status_code=400, detail=f"Gmail API error: {str(e)}"
            )

    def _extract_body(self, payload) -> str:
        """Extract email body from payload."""
        body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if "data" in part["body"]:
                        body = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                        break
        elif payload["mimeType"] == "text/plain":
            if "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                    "utf-8"
                )

        return body

    def search_financial_emails(
        self, additional_query: str = "", max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for financial-related emails."""
        financial_keywords = [
            "from:bank",
            "from:paypal",
            "from:venmo",
            "from:stripe",
            "subject:receipt",
            "subject:invoice",
            "subject:payment",
            "subject:transaction",
            "from:amazon",
        ]

        # Combine financial keywords with user query
        base_query = " OR ".join(financial_keywords)
        full_query = f"({base_query})"
        if additional_query:
            full_query += f" {additional_query}"

        return self.get_emails(full_query, max_results)