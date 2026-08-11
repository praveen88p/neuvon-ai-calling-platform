"""Google Sheets API v4 async wrapper.

All blocking IO is wrapped in ``asyncio.to_thread()`` so the FastAPI
event loop is never blocked — pattern taken from Voice-TimeLogger repo's
``GoogleSheetsStorage`` class.

Credentials come from the database per-connection (not from a file on disk).
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.logging import logger


# ── Scopes ────────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ── Helpers ───────────────────────────────────────────────────────────────

_SHEET_URL_RE = re.compile(
    r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"
)


def extract_spreadsheet_id(url: str) -> str:
    """Extract spreadsheet ID from a full Google Sheets URL."""
    match = _SHEET_URL_RE.search(url)
    if not match:
        raise SheetClientError(f"Invalid Google Sheets URL: {url}")
    return match.group(1)


def col_index_to_letter(index: int) -> str:
    """Convert 0-based column index to column letter (A, B, ..., Z, AA, AB...).

    More robust than ``chr(65 + index)`` from kaymen99 repo which breaks
    for columns beyond Z.
    """
    result = ""
    while True:
        result = chr(65 + (index % 26)) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result


# ── Errors ────────────────────────────────────────────────────────────────


class SheetClientError(Exception):
    """Base error for Google Sheets operations."""

    def __init__(self, message: str, *, code: str = "SHEET_ERROR") -> None:
        self.code = code
        super().__init__(message)


class SheetAuthError(SheetClientError):
    """Credentials are invalid or expired."""

    def __init__(self, message: str = "Google Sheets auth failed") -> None:
        super().__init__(message, code="SHEET_AUTH_ERROR")


class SheetNotFoundError(SheetClientError):
    """Spreadsheet or sheet tab not found."""

    def __init__(self, message: str = "Spreadsheet not found") -> None:
        super().__init__(message, code="SHEET_NOT_FOUND")


# ── Data classes ──────────────────────────────────────────────────────────


class CellUpdate:
    """A single cell update for batch operations."""

    __slots__ = ("sheet_name", "col_letter", "row_number", "value")

    def __init__(
        self, sheet_name: str, col_letter: str, row_number: int, value: str
    ) -> None:
        self.sheet_name = sheet_name
        self.col_letter = col_letter
        self.row_number = row_number
        self.value = value


# ── Client ────────────────────────────────────────────────────────────────


class GoogleSheetsClient:
    """Async wrapper around Google Sheets API v4.

    Usage::

        client = GoogleSheetsClient(credentials_json, spreadsheet_id)
        await client.connect()  # validates access
        headers = await client.read_headers("Sheet1")
        rows = await client.read_rows("Sheet1", start_row=2)
        await client.update_cells("Sheet1", [CellUpdate(...)])
    """

    def __init__(self, credentials_json: str, spreadsheet_id: str) -> None:
        self._creds_json = credentials_json
        self.spreadsheet_id = spreadsheet_id
        self._service: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Build the Sheets API service (runs in thread)."""
        try:
            self._service = await asyncio.to_thread(self._build_service)
            logger.info(
                "sheets_client.connected",
                spreadsheet_id=self.spreadsheet_id,
            )
        except Exception as exc:
            logger.error(
                "sheets_client.connect_failed",
                spreadsheet_id=self.spreadsheet_id,
                error=str(exc),
            )
            raise SheetAuthError(f"Failed to connect: {exc}") from exc

    def _build_service(self) -> Any:
        """Synchronous: create Google API service from JSON credentials."""
        info = json.loads(self._creds_json)
        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def _ensure_connected(self) -> None:
        if self._service is None:
            raise SheetClientError("Not connected. Call connect() first.")

    # ── Read operations ───────────────────────────────────────────────

    async def get_sheet_names(self) -> list[str]:
        """Return list of sheet tab names in the spreadsheet."""
        self._ensure_connected()
        try:
            return await asyncio.to_thread(self._get_sheet_names_sync)
        except HttpError as exc:
            self._handle_http_error(exc)
            raise  # unreachable but keeps type checker happy

    def _get_sheet_names_sync(self) -> list[str]:
        metadata = (
            self._service.spreadsheets()
            .get(spreadsheetId=self.spreadsheet_id)
            .execute()
        )
        return [
            sheet["properties"]["title"]
            for sheet in metadata.get("sheets", [])
        ]

    async def read_headers(self, sheet_name: str) -> list[str]:
        """Read the first row (header row) of a sheet tab."""
        self._ensure_connected()
        try:
            return await asyncio.to_thread(self._read_headers_sync, sheet_name)
        except HttpError as exc:
            self._handle_http_error(exc)
            raise

    def _read_headers_sync(self, sheet_name: str) -> list[str]:
        result = (
            self._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!1:1",
            )
            .execute()
        )
        rows = result.get("values", [])
        return rows[0] if rows else []

    async def read_rows(
        self, sheet_name: str, start_row: int = 2, end_row: int | None = None
    ) -> list[list[str]]:
        """Read data rows (excluding header). Returns list of rows.

        ``start_row`` is 1-indexed (row 2 = first data row).
        """
        self._ensure_connected()
        try:
            return await asyncio.to_thread(
                self._read_rows_sync, sheet_name, start_row, end_row
            )
        except HttpError as exc:
            self._handle_http_error(exc)
            raise

    def _read_rows_sync(
        self, sheet_name: str, start_row: int, end_row: int | None
    ) -> list[list[str]]:
        range_str = f"{sheet_name}!A{start_row}:ZZ"
        if end_row:
            range_str = f"{sheet_name}!A{start_row}:ZZ{end_row}"

        result = (
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_str)
            .execute()
        )
        return result.get("values", [])

    async def get_row_count(self, sheet_name: str) -> int:
        """Get total number of rows (including header) in the sheet."""
        self._ensure_connected()
        try:
            return await asyncio.to_thread(self._get_row_count_sync, sheet_name)
        except HttpError as exc:
            self._handle_http_error(exc)
            raise

    def _get_row_count_sync(self, sheet_name: str) -> int:
        result = (
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=sheet_name)
            .execute()
        )
        rows = result.get("values", [])
        return len(rows)

    # ── Write operations ──────────────────────────────────────────────

    async def update_cells(
        self, sheet_name: str, updates: list[CellUpdate]
    ) -> None:
        """Batch update multiple cells.

        Pattern from kaymen99 repo's ``update_record()`` — uses
        ``batchUpdate`` for efficiency (one API call for N cells).
        """
        if not updates:
            return
        self._ensure_connected()
        try:
            await asyncio.to_thread(self._update_cells_sync, sheet_name, updates)
        except HttpError as exc:
            self._handle_http_error(exc)
            raise

    def _update_cells_sync(
        self, sheet_name: str, updates: list[CellUpdate]
    ) -> None:
        data = [
            {
                "range": f"{sheet_name}!{u.col_letter}{u.row_number}",
                "values": [[u.value]],
            }
            for u in updates
        ]
        body = {"valueInputOption": "USER_ENTERED", "data": data}
        self._service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body=body
        ).execute()

    # ── Error handling ────────────────────────────────────────────────

    def _handle_http_error(self, exc: HttpError) -> None:
        """Convert Google API HTTP errors to our custom errors."""
        status_code = exc.resp.status if exc.resp else 0
        if status_code == 401 or status_code == 403:
            raise SheetAuthError(
                f"Google Sheets permission denied (HTTP {status_code})"
            ) from exc
        if status_code == 404:
            raise SheetNotFoundError(
                f"Spreadsheet not found: {self.spreadsheet_id}"
            ) from exc
        raise SheetClientError(
            f"Google Sheets API error (HTTP {status_code}): {exc}",
            code="GOOGLE_API_ERROR",
        ) from exc
