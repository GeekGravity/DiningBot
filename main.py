"""DiningBot entry point that fetches today's menu and emails it."""

import argparse
import datetime as _dt
import logging
import zoneinfo
from typing import Optional, Sequence

from dotenv import load_dotenv

from diningbot.fetch_menu import fetch_daily_menu
from diningbot.extraction import extract_specials
from diningbot.menu_renderer import render_html
from diningbot.emailer import (
    load_cached_email_html,
    send_email,
    send_email_to_one,
)

_logger = logging.getLogger(__name__)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send today's dining menu to subscribers or a single email."
    )
    parser.add_argument(
        "--one-off",
        metavar="EMAIL",
        help="Send today's cached menu HTML to a single email address.",
    )
    return parser.parse_args(argv)


def _run_daily() -> int:
    pacific = zoneinfo.ZoneInfo("America/Los_Angeles")
    date = _dt.date.today().isoformat()

    try:
        periods = fetch_daily_menu(date)
        periods = extract_specials(periods)
    except RuntimeError as exc:
        _logger.error("Failed to fetch periods for %s: %s", date, exc)
        return 1

    html_output = render_html(date, periods)

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


def _run_one_off(email: str) -> int:
    pacific = zoneinfo.ZoneInfo("America/Los_Angeles")
    date = _dt.datetime.now(pacific).date().isoformat()

    html_output = load_cached_email_html(date)
    if not html_output:
        _logger.info("No cached HTML found for %s; skipping one-off send.", date)
        return 0

    try:
        send_email_to_one(email, html_output, date)
    except RuntimeError as exc:
        _logger.error("Failed to send email: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - network side effects
        _logger.error("Failed to send email: %s", exc)
        return 1

    _logger.info("Dining menu email sent to %s for %s", email, date)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    args = _parse_args(argv)

    if args.one_off:
        return _run_one_off(args.one_off)
    return _run_daily()


if __name__ == "__main__":
    raise SystemExit(main())
