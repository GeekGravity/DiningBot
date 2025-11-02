"""API client for Dine On Campus endpoints.

Focuses on the periods (menu) endpoint for a specific location.
"""

from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

_logger = logging.getLogger(__name__)

BASE_URL = "https://api.dineoncampus.ca/v1"


class ApiError(RuntimeError):
    pass


@dataclass
class MenuItem:
    name: str
    description: Optional[str] = None


@dataclass
class Category:
    id: Optional[str]
    name: str
    items: List[MenuItem]


@dataclass
class Period:
    id: Optional[str]
    name: str
    sort_order: int
    categories: List[Category]


@dataclass
class Menu:
    date: str
    periods: List[Period]


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def fetch_menu(location_id: str, *, date: Optional[str] = None, platform: int = 0, timeout: int = 20) -> Dict[str, Any]:
    """Fetch raw menu JSON for a given location and date.

    - location_id: API location identifier
    - date: YYYY-MM-DD; defaults to today in local time
    - platform: API expects an integer platform flag (0 works for web)
    """

    if not date:
        date = _dt.date.today().isoformat()

    url = f"{BASE_URL}/location/{location_id}/periods"
    params = {"platform": platform, "date": date}
    headers = {
        "User-Agent": "DiningBot/0.2",
        "Accept": "application/json, text/plain, */*",
    }
    _logger.info("GET %s params=%s", url, params)
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Failed request to {url}") from exc

    ct = resp.headers.get("Content-Type", "")
    if resp.status_code != 200 or "application/json" not in ct:
        raise ApiError(f"Unexpected response {resp.status_code} {ct}: {resp.text[:200]}")

    data = resp.json()
    if data.get("status") != "success":
        raise ApiError(f"API error: {data}")
    return data


def parse_menu(data: Dict[str, Any]) -> Menu:
    """Convert raw JSON into typed dataclasses with tolerant shape handling."""
    menu = data.get("menu") or {}
    date = menu.get("date", "")
    periods_raw = _ensure_list(menu.get("periods"))
    periods: List[Period] = []
    for p in periods_raw:
        pid = (p or {}).get("id")
        name = (p or {}).get("name", "")
        order = int((p or {}).get("sort_order", 0) or 0)
        categories_raw = _ensure_list((p or {}).get("categories"))
        categories: List[Category] = []
        for c in categories_raw:
            cid = (c or {}).get("id")
            cname = (c or {}).get("name", "")
            items_raw = _ensure_list((c or {}).get("items"))
            items: List[MenuItem] = []
            for it in items_raw:
                if not it:
                    continue
                iname = (it or {}).get("name") or (it or {}).get("item") or ""
                idesc = (it or {}).get("description")
                items.append(MenuItem(name=iname, description=idesc))
            categories.append(Category(id=cid, name=cname, items=items))
        periods.append(Period(id=pid, name=name, sort_order=order, categories=categories))
    periods.sort(key=lambda x: x.sort_order)
    return Menu(date=date, periods=periods)


def summarize_menu(menu: Menu) -> str:
    lines: List[str] = []
    lines.append(f"Date: {menu.date}")
    for period in menu.periods:
        lines.append(f"\n== {period.name} ==")
        for cat in period.categories:
            lines.append(f"  - {cat.name}")
            for item in cat.items[:20]:
                lines.append(f"      - {item.name}")
    return "\n".join(lines)


def fetch_period(location_id: str, period_id: str, *, date: Optional[str] = None, platform: int = 0, timeout: int = 20) -> Dict[str, Any]:
    """Fetch raw JSON for a single period within a location and date.

    Calls: /v1/location/{location_id}/periods/{period_id}?platform=0&date=YYYY-MM-DD
    """
    if not date:
        date = _dt.date.today().isoformat()

    url = f"{BASE_URL}/location/{location_id}/periods/{period_id}"
    params = {"platform": platform, "date": date}
    headers = {
        "User-Agent": "DiningBot/0.2",
        "Accept": "application/json, text/plain, */*",
    }
    _logger.info("GET %s params=%s", url, params)
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Failed request to {url}") from exc

    ct = resp.headers.get("Content-Type", "")
    if resp.status_code != 200 or "application/json" not in ct:
        raise ApiError(f"Unexpected response {resp.status_code} {ct}: {resp.text[:200]}")

    data = resp.json()
    if data.get("status") != "success":
        raise ApiError(f"API error: {data}")
    return data


def parse_period(data: Dict[str, Any]) -> Period:
    """Parse a single period JSON into a Period dataclass.

    Handles multiple shapes by probing keys.
    """
    period_obj: Dict[str, Any] = {}
    menu = data.get("menu") if isinstance(data, dict) else None
    if isinstance(data, dict) and data.get("period"):
        period_obj = data.get("period") or {}
    elif isinstance(menu, dict) and menu.get("periods"):
        periods_raw = _ensure_list(menu.get("periods"))
        period_obj = (periods_raw[0] if periods_raw else {}) or {}
    elif isinstance(data, dict) and data.get("categories"):
        period_obj = data

    pid = period_obj.get("id")
    name = period_obj.get("name", "")
    order = int((period_obj.get("sort_order", 0) or 0))
    categories_raw = _ensure_list(period_obj.get("categories"))
    categories: List[Category] = []
    for c in categories_raw:
        if not c:
            continue
        cid = c.get("id")
        cname = c.get("name", "")
        items_raw = _ensure_list(c.get("items"))
        items: List[MenuItem] = []
        for it in items_raw:
            if not it:
                continue
            iname = (it or {}).get("name") or (it or {}).get("item") or ""
            idesc = (it or {}).get("description")
            items.append(MenuItem(name=iname, description=idesc))
        categories.append(Category(id=cid, name=cname, items=items))
    return Period(id=pid, name=name, sort_order=order, categories=categories)


def summarize_period(period: Period, *, date: Optional[str] = None) -> str:
    lines: List[str] = []
    if date:
        lines.append(f"Date: {date}")
    lines.append(f"== {period.name} ==")
    for cat in period.categories:
        lines.append(f"  - {cat.name}")
        for item in cat.items[:20]:
            lines.append(f"      - {item.name}")
    return "\n".join(lines)
