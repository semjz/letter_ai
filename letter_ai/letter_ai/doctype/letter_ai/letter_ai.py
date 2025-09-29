# Copyright (c) 2025, saman and contributors
# For license information, please see license.txt

from datetime import date, datetime
import frappe
from frappe import _
from frappe.model.document import Document
from .djalali_georgian_conversion import (
    parse_jalali_to_greg_iso,     # '1404/06/25' -> '2025-09-15'
    greg_iso_to_jalali_str        # '2025-09-15' -> '1404/06/25'
)

NO_PROMPT_TYPES = {"گزارش", "معرفی", "بارگیری", "گواهی اشتغال به کار"}

def _to_iso_date(val):
    if hasattr(val, "isoformat"):  # date or datetime
        return val.date().isoformat() if hasattr(val, "date") else val.isoformat()
    return (val or "").strip()

class letter_ai(Document):
    def validate(self):
        # Checks only
        self.ref_letter = (self.ref_letter or "").strip()
        has_ref = bool(self.ref_letter)
        has_any_date = bool((self.ref_date_djalali or "").strip() or self.ref_date)
        if has_ref ^ has_any_date:
            frappe.throw("لطفا هر دو فیلد «نامه مرجع» و «تاریخ مرجع» را با هم پر کنید.")
        if self.letter_type not in NO_PROMPT_TYPES and not (self.prompt or "").strip():
            frappe.throw(_("Prompt is required for letter type: {0}").format(self.letter_type))

    def before_save(self):
        # Mutations/normalization
        jalali_text = (self.ref_date_djalali or "").strip()
        if jalali_text:
            iso = parse_jalali_to_greg_iso(jalali_text)
            self.ref_date = iso
            self.ref_date_djalali = greg_iso_to_jalali_str(iso)
        elif self.ref_date:
            iso = _to_iso_date(self.ref_date)
            self.ref_date = iso
            self.ref_date_djalali = greg_iso_to_jalali_str(iso)
        else:
            self.ref_date = ""
            self.ref_date_djalali = ""

    def onload(self):
        # Read-time mirror for UI convenience
        if self.get("ref_date"):
            iso = _to_iso_date(self.ref_date)
            self.ref_date_djalali = greg_iso_to_jalali_str(iso)
