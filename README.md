# AI Receipt Parser & Bill Splitter CLI (Gemini Vision)

Extract structured itemized restaurant/bar/grocery receipts from photos into clean JSON using `gemini-3.5-flash-lite` structured outputs — no paid OCR APIs or Splitwise subscriptions.

## 👉 Want friends to tap their own dishes right inside a Telegram group chat?
Snap 1 receipt photo and drop the interactive bill into any group chat (2 free scans, friends tap for free):  
➡️ **[Open @Drat7robot in Telegram](https://t.me/Drat7robot?start=github)**

## Quick Start
```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your_api_key"
python cli_receipt_split.py receipt.jpg
```
