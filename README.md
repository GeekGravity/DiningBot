# DiningBot (API-Only, Windows)

Minimal CLI to fetch menu data directly from the Dine On Campus API and print a readable summary. No scraping or browser automation.

## Prerequisites

- Windows 10/11 with PowerShell 5+ (PowerShell 7 works too)
- Python 3.10 or newer installed and available via the `py` launcher

## Project Layout

- `main.py` – CLI entry point.
- `diningbot/api.py` – API client and summary formatter.
- `requirements.txt` – Dependencies (`requests` only).
- `.env.example` – Sample environment variables for SMTP/email.

## Setup (PowerShell)

1. **Clone or download the repo** into a convenient directory, e.g. `C:\Users\you\Documents\DiningBot`.
2. **Create and activate a virtual environment**:
   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1   # For Command Prompt use .\.venv\Scripts\activate.bat
   ```
3. **Install dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Configure environment**:
   ```powershell
   Copy-Item .env.example .env
   ```
   Edit `.env` with your SMTP credentials and recipients.

## Fetch Today’s Menu (HTML output)

The CLI fetches breakfast, lunch, and dinner for today (SFU Dining) and renders an email-friendly HTML summary (inline styles, table layout).

```powershell
# Print HTML to the console
python main.py

# Write the HTML to a file
python main.py --output menu.html

# Inspect raw JSON payloads instead of HTML
python main.py --json
```

- Uses today’s date automatically.
- `platform=0` is set automatically.
- An email is sent on each run when SMTP settings are configured (see below).

### Email configuration

Populate `.env` (see `.env.example`) with SMTP details. The script loads `.env` automatically via `python-dotenv`.

- Set `--skip-email` if you want to suppress sending for a specific run.
- Override the subject line with `--subject "Custom subject"`.

## Next Steps

- Schedule `python main.py --output menu.html` via Windows Task Scheduler and attach the file to an email or post it to a web page.
