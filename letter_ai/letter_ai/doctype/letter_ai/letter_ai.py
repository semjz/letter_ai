# Copyright (c) 2025, saman and contributors
# For license information, please see license.txt

from __future__ import annotations
from frappe import _
import frappe
from frappe.model.document import Document
from .djalali_georgian_conversion import (
    parse_jalali_to_greg_iso,     # '1404/06/25' -> '2025-09-15'
    greg_iso_to_jalali_str        # '2025-09-15' -> '1404/06/25'
)

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("controller", allow_site=True, file_count=50)


class letter_ai(Document):
	def validate(self):
		"""Validate pair rule, parse Jalali input, and keep mirrors in sync."""
		# Normalize inputs
		self.ref_letter = (self.ref_letter or "").strip()
		jalali_text = (self.ref_date_djalali or "").strip()

		# --- (1) Pair rule: either both present or both empty
		has_ref = bool(self.ref_letter)
		has_date = bool(jalali_text)
		if has_ref ^ has_date:
			frappe.throw("لطفا هر دو فیلد «نامه مرجع» و «تاریخ مرجع» را با هم پر کنید.")

		if jalali_text:
			greg_iso = parse_jalali_to_greg_iso(jalali_text)
			self.ref_date = greg_iso
			self.ref_date_djalali = greg_iso_to_jalali_str(greg_iso)
		elif self.ref_date:
			self.ref_date_djalali = greg_iso_to_jalali_str(self.ref_date)
		else:
			self.ref_date_djalali = ""   # keep both empty cleanly

		if self.letter_type not in ["گزارش", "معرفی", "بارگیری", "گواهی اشتغال به کار"] and not self.prompt:
			frappe.throw(_("Prompt is required for letter type: {0}").format(self.letter_type))
		# Log for debugging
		logger.info({
		"ref_letter": self.ref_letter,
		"ref_date_djalali_in": jalali_text,
		"ref_date_out_greg": self.ref_date,
		"ref_date_djalali_out": self.ref_date_djalali,
		})

	def onload(self):
		"""
		Optional: when opening the form, ensure the Jalali mirror shows
		the current DB value if user didn’t type it this session.
		"""
		if self.get("ref_date"):
			self.ref_date_djalali = greg_iso_to_jalali_str(self.ref_date)
