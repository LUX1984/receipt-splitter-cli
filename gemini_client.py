from __future__ import annotations

import asyncio
import base64
import json
import aiohttp
from aiohttp_socks import ProxyConnector


class GeminiQuotaError(RuntimeError):
    pass


class GeminiAPIError(RuntimeError):
    pass


RECEIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_receipt": {"type": "boolean"},
        "venue": {"type": "string"},
        "currency": {"type": "string"},
        "discount": {"type": "number"},
        "service_fee": {"type": "number"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "qty": {"type": "number"},
                    "total_price": {"type": "number"},
                },
                "required": ["name", "qty", "total_price"],
            },
        },
    },
    "required": ["is_receipt", "venue", "currency", "discount", "service_fee", "items"],
}


class GeminiReceiptParser:
    BASE_URL = "https://generativelanguage.googleapis.com"
    MODEL = "gemini-3.5-flash-lite"

    def __init__(self, api_key: str, timeout_sec: int = 60, proxy_url: str = "") -> None:
        self.api_key = api_key
        self.proxy_url = proxy_url.strip()
        self.timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async def parse_receipt(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        if not image_bytes:
            raise GeminiAPIError("Empty image")

        prompt = (
            "Extract all purchased line items from this receipt or bill photo.\n"
            "Rules:\n"
            "- Set is_receipt=false if the image is clearly NOT a receipt, bill, invoice, or order summary.\n"
            "- Merge identical duplicate lines if needed, keep item names short and clean in original language.\n"
            "- total_price is the line total (quantity * unit price) after line-level discount.\n"
            "- Put overall bill-level discount in discount (>=0) and service charge/mandatory fee in service_fee (>=0).\n"
            "- Use currency symbol like ₽, $, €, ₸, ₺, AED, GEL, etc."
        )
        payload = {
            "model": self.MODEL,
            "input": [
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                    "mime_type": mime_type,
                },
            ],
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": RECEIPT_SCHEMA,
            },
        }
        connector = ProxyConnector.from_url(self.proxy_url, rdns=True) if self.proxy_url else None
        async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
            data = await self._post_with_retry(session, payload)

        raw_text = ""
        for step in data.get("steps", []):
            for item in step.get("content", []):
                if item.get("text"):
                    raw_text += item["text"]
        if not raw_text:
            raise GeminiAPIError("Empty response from Gemini")
        return json.loads(raw_text)

    async def _post_with_retry(self, session: aiohttp.ClientSession, payload: dict, max_attempts: int = 3) -> dict:
        url = f"{self.BASE_URL}/v1beta/interactions"
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        last_err = ""
        for attempt in range(max_attempts):
            async with session.post(url, headers=headers, json=payload) as resp:
                body = await resp.text()
                if resp.status == 200:
                    return json.loads(body)
                last_err = f"HTTP {resp.status}: {body[:260]}"
                if resp.status == 429:
                    if "limit: 0" in body:
                        raise GeminiQuotaError(last_err)
                    if attempt + 1 < max_attempts:
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue
                    raise GeminiQuotaError(last_err)
                if resp.status >= 500 and attempt + 1 < max_attempts:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise GeminiAPIError(last_err)
        raise GeminiAPIError(last_err)
