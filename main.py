"""DiningBot entry point that fetches today's menu and emails it."""

import datetime as _dt
import zoneinfo
import logging

from dotenv import load_dotenv

from diningbot.fetch_menu import fetch_daily_menu
from diningbot.extraction import extract_specials
from diningbot.menu_renderer import render_html
from diningbot.emailer import send_email

_logger = logging.getLogger(__name__)


def main() -> int:

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    pacific = zoneinfo.ZoneInfo("America/Los_Angeles")
    date = _dt.date.today().isoformat()

    # Fetch and parse menu
    try:
        periods = fetch_daily_menu(date)
        periods = extract_specials(periods)
    except RuntimeError as exc:
        _logger.error("Failed to fetch periods for %s: %s", date, exc)
        return 1

    # Generate email content
    html_output = render_html(date, periods)

    # Send the email
    try:
        send_email(date, html_output, periods)
    except RuntimeError as exc:
        _logger.error("%s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - network side effects
        _logger.error("Failed to send email: %s", exc)
        return 1

    _logger.info("Dining menu email sent for %s", date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
