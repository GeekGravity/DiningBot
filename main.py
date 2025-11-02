"""Fetch SFU Dining menus (breakfast/lunch/dinner) and render HTML."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from html import escape

from dotenv import load_dotenv

from diningbot import api as dine_api
from diningbot import emailer

# Fixed campus/location and known period IDs (SFU Dining)
DEFAULT_LOCATION_ID = "63fd054f92d6b41e84b6c30e"
PERIOD_ALIASES = {
    "breakfast": "6906a2465155390520327829",
    "lunch": "6906a2465155390520327836",
    "dinner": "6906a247515539052032784d",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch today's SFU Dining menu (breakfast, lunch, dinner) and output HTML"
    )
    parser.add_argument("--date", help="YYYY-MM-DD (defaults to today)")
    parser.add_argument("--output", help="Write HTML to the given file path. Defaults to stdout.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON for all periods instead of HTML")
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Do not send email (default is to send if SMTP settings are configured).",
    )
    parser.add_argument(
        "--subject",
        help="Override email subject (defaults to 'SFU Dining - <date>').",
    )
    return parser


def render_html(date: str, period_map: dict[str, dine_api.Period]) -> str:  # type: ignore[attr-defined]
    def table_section(period_key: str, period: dine_api.Period) -> str:  # type: ignore[attr-defined]
        header = escape(period.name or period_key.title())
        rows: list[str] = [
            "<tr>"
            f"<th colspan=\"2\" style=\"background-color:#1f2937;color:#ffffff;padding:12px 16px;"
            "font-size:18px;text-align:left;border-top-left-radius:12px;border-top-right-radius:12px;\">"
            f"{header}</th></tr>"
        ]

        if period.categories:
            for category in period.categories:
                if not category.items:
                    continue
                cat_name = escape(category.name or "Miscellaneous")
                items_markup: list[str] = []
                for item in category.items:
                    line = escape(item.name or "Unnamed item")
                    if item.description:
                        line += f"<span style=\"color:#5f6368;font-size:13px;\"> - {escape(item.description)}</span>"
                    items_markup.append(f"<li style=\"margin-bottom:6px;\">{line}</li>")
                rows.append(
                    "<tr>"
                    f"<td style=\"vertical-align:top;padding:12px 16px;font-weight:bold;color:#111827;width:32%;"
                    f"background-color:#f1f5f9;\">{cat_name}</td>"
                    f"<td style=\"vertical-align:top;padding:12px 16px;background-color:#ffffff;\">"
                    f"<ul style=\"margin:0;padding-left:18px;color:#303133;\">{''.join(items_markup)}</ul>"
                    "</td>"
                    "</tr>"
                )
        else:
            rows.append(
                "<tr><td colspan=\"2\" style=\"padding:14px 16px;background-color:#ffffff;color:#374151;\">"
                "Menu details are not available for this period.</td></tr>"
            )

        rows.append(
            "<tr><td colspan=\"2\" style=\"height:12px;background-color:#ffffff;border-bottom-left-radius:12px;"
            "border-bottom-right-radius:12px;\"></td></tr>"
        )

        return (
            "<table role=\"presentation\" style=\"width:100%;max-width:640px;margin:0 auto 18px auto;"
            "border-collapse:separate;border-spacing:0;font-family:Arial,Helvetica,sans-serif;"
            "background-color:#ffffff;box-shadow:0 6px 16px rgba(15,23,42,0.1);border-radius:12px;\">"
            f"{''.join(rows)}"
            "</table>"
        )

    sections = []
    for key in ("breakfast", "lunch", "dinner"):
        period = period_map.get(key)
        if period:
            sections.append(table_section(key, period))

    header_block = (
        "<table role=\"presentation\" style=\"margin:0 auto 24px auto;text-align:center;\">"
        "<tr><td style=\"font-size:24px;color:#111827;font-weight:bold;\">SFU Dining - "
        f"{escape(date)}</td></tr>"
        "<tr><td style=\"font-size:14px;color:#4b5563;padding-top:6px;\">Daily menu summary</td></tr>"
        "</table>"
    )

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <meta http-equiv=\"x-ua-compatible\" content=\"ie=edge\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        f"  <title>SFU Dining - {escape(date)}</title>",
        "</head>",
        "<body style=\"margin:0;padding:24px;background-color:#edf2f7;font-family:Arial,Helvetica,sans-serif;\">",
        "  <center style=\"width:100%;\">",
        f"    {header_block}",
        *sections,
        "  </center>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    date = args.date or _dt.date.today().isoformat()
    raw_payloads: dict[str, dict] = {}
    parsed_periods: dict[str, dine_api.Period] = {}  # type: ignore[attr-defined]

    def _fetch(key: str, period_id: str) -> tuple[str, dict]:
        data = dine_api.fetch_period(DEFAULT_LOCATION_ID, period_id, date=date, platform=0)
        return key, data

    with ThreadPoolExecutor(max_workers=len(PERIOD_ALIASES)) as executor:
        futures = {executor.submit(_fetch, key, period_id): key for key, period_id in PERIOD_ALIASES.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                k, data = future.result()
            except dine_api.ApiError as exc:  # type: ignore[attr-defined]
                print(f"API error retrieving {key}: {exc}")
                return 1
            raw_payloads[k] = data
            parsed_periods[k] = dine_api.parse_period(data)

    if args.json:
        print(json.dumps(raw_payloads, indent=2))
        return 0

    html_output = render_html(date, parsed_periods)
    if args.output:
        Path(args.output).write_text(html_output, encoding="utf-8")
    else:
        print(html_output)

    if not args.skip_email:
        try:
            settings = emailer.load_email_settings()
        except ValueError as exc:
            print(f"Skipping email: {exc}")
        else:
            subject = args.subject or f"SFU Dining - {date}"
            text_lines = [subject, ""]
            for key in ("breakfast", "lunch", "dinner"):
                period = parsed_periods.get(key)
                if not period:
                    continue
                text_lines.append(period.name or key.title())
                for category in period.categories:
                    if not category.items:
                        continue
                    item_names = ", ".join(item.name for item in category.items if item.name)
                    if item_names:
                        label = category.name or "Misc"
                        text_lines.append(f"  {label}: {item_names}")
                text_lines.append("")
            plain_text = "\n".join(text_lines).strip()
            try:
                emailer.send_email(settings, subject, html_output, plain_text)
            except Exception as exc:  # pragma: no cover - network side effects
                print(f"Failed to send email: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
