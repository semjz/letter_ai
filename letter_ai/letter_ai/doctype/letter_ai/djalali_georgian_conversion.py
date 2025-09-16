# Copyright (c) 2025, saman and contributors
# For license information, please see license.txt

from __future__ import annotations          # 1) future-proof typing (safe to keep)

import re                                   # 2) we'll use regex to validate the Jalali format
import datetime                             # 3) needed for Gregorian->Jalali conversion
import frappe                               # 4) frappe API (throw, Doc events, etc.)
from frappe.model.document import Document   # 5) base class for DocTypes

try:
    import jdatetime                        # 6) Jalali/Gregorian conversions
except ImportError:
    jdatetime = None                        # 7) handle missing dependency gracefully

# Accept 1404/06/25 or 1404-6-25 (Persian/Arabic digits also allowed)
JALALI_RE = re.compile(r"^\s*(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\s*$")


def _fa_to_en_digits(s: str) -> str:
    """Convert Persian/Arabic digits to ASCII so parsing works reliably."""
    if not s:
        return s
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return s.translate(trans)


def parse_jalali_to_greg_iso(jalali_str: str) -> str:
    """
    Input: '1404/06/25' (or '1404-06-25', Persian digits OK)
    Output: 'YYYY-MM-DD' (Gregorian) for saving into a Date field
    Raises frappe.ValidationError on bad input
    """
    if not jdatetime:
        frappe.throw("کتابخانه jdatetime نصب نشده است. لطفاً آن را به requirements اضافه و نصب کنید.")

    s = _fa_to_en_digits(jalali_str or "").strip().replace("-", "/")

    m = JALALI_RE.match(s)
    if not m:
        frappe.throw("فرمت تاریخ جلالی نامعتبر است. نمونه صحیح: 1404/06/25")

    jy, jm, jd = map(int, m.groups())
    try:
        gdate = jdatetime.date(jy, jm, jd).togregorian()  # -> datetime.date
    except Exception:
        frappe.throw("تاریخ جلالی نامعتبر است (روز/ماه خارج از محدوده).")

    return gdate.strftime("%Y-%m-%d")


def greg_iso_to_jalali_str(greg_iso: str) -> str:
    """
    Input: 'YYYY-MM-DD' (from DB)
    Output: 'YYYY/MM/DD' in Jalali (for showing in the Data field)
    """
    if not jdatetime or not greg_iso:
        return ""
    try:
        y, m, d = map(int, greg_iso.split("-"))
        g = datetime.date(y, m, d)
        j = jdatetime.date.fromgregorian(date=g)
        return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
    except Exception:
        return ""

