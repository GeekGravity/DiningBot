# DiningBot

DiningBot automatically pulls SFU Dining Commons menus from the official Dine On Campus API and emails students the daily breakfast, lunch, and dinner menus. Every morning, subscribers get a clean summary of what’s being served before they even show up.

## Prerequisites

- Windows 10 or Windows 11 with PowerShell
- Python 3.10 or newer
- An SMTP account that allows sending mail from the machine running the program.

## Installation Setup

1. Clone or download the repository:

   ```powershell
   git clone https://github.com/GeekGravity/DiningBot.git
   cd DiningBot
   ```

2. Create an isolated virtual environment:
   ```powershell
   py -3 -m venv .venv
   ```
3. Activate the virtual environment for your session:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
4. Install the Python dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Create a virtual environment file and populate it with the following variables:
   ```powershell
   DININGBOT_SMTP_HOST=
   DININGBOT_SMTP_PORT=
   DININGBOT_SMTP_USE_TLS=
   DININGBOT_SMTP_USER=
   DININGBOT_SMTP_PASSWORD=
   DININGBOT_EMAIL_SENDER=
   DININGBOT_EMAIL_RECIPIENTS=
   ```

## Configure Email Delivery

DiningBot loads everything it needs from environment variables (the `.env` file is read automatically at startup).

| Variable                     | Required | Description                                             |
| ---------------------------- | -------- | ------------------------------------------------------- |
| `DININGBOT_SMTP_HOST`        | yes      | SMTP server hostname (for example `smtp.gmail.com`).    |
| `DININGBOT_SMTP_PORT`        | no       | Port number, defaults to `587`.                         |
| `DININGBOT_EMAIL_SENDER`     | yes      | From address shown to recipients.                       |
| `DININGBOT_EMAIL_RECIPIENTS` | yes      | Comma-separated list of inboxes to receive the menu.    |
| `DININGBOT_SMTP_USER`        | no       | Username for authenticated SMTP providers.              |
| `DININGBOT_SMTP_PASSWORD`    | no       | Password or app-specific token for the account above.   |
| `DININGBOT_SMTP_USE_TLS`     | no       | Set to `false` to disable STARTTLS (default is `true`). |

Tip: When using Gmail or Outlook, create an app password and store it in the `.env` file rather than your main password.

## Running the Program

1. Ensure the virtual environment is active (`.\.venv\Scripts\Activate.ps1`) and that `.env` contains valid credentials.
2. Execute the entry point:
   ```powershell
   python main.py
   ```
3. On success you will see `INFO` logs indicating that the dining menu email was sent. If anything fails it logs an error and returns a non-zero exit code.
