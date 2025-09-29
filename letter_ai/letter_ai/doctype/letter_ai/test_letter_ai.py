# -*- coding: utf-8 -*-
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.exceptions import ValidationError
from frappe.utils import nowdate

# Use the DocType title exactly as in your JSON/Desk
DOCTYPE_NAME = "letter_ai"  # change to "letter ai" if that's your actual title

class TestLetterAI(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.db.rollback()

    def setUp(self):
        frappe.db.rollback()

        # --- create required linked masters (no guards/skips) ---
        # Company (minimal for ERPNext v15; add fields if your site enforces more)
        self.company = frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.company = frappe.get_doc({
                "doctype": "Company",
                "company_name": "Test Company",
                "abbr": "TC",
                "default_currency": "USD",
                "country": "United States",
            }).insert(ignore_permissions=True).name

        # Employee
        self.employee = frappe.db.get_value("Employee", {}, "name")
        if not self.employee:
            self.employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": "Test Employee",
                "company": self.company,
                "date_of_joining": nowdate(),
            }).insert(ignore_permissions=True).name

    def _new_doc(self, **kwargs):
        """Build a valid Letter AI doc with sensible defaults that satisfy schema + controller."""
        defaults = dict(
            doctype=DOCTYPE_NAME,
            letter_name="LT-" + frappe.generate_hash(length=8),
            # allowed values from your Select fields:
            letter_type="معرفی",            # one of your allowed types that DOES NOT require prompt
            tone_of_writing="اداری",
            # required Link fields:
            sender=self.employee,
            recipient_company=self.company,
            # controller fields:
            prompt="",                      # allowed empty for "معرفی"
            ref_letter="",
            ref_date="",
            ref_date_djalali="",
            generated_letter="",
        )
        defaults.update(kwargs)
        return frappe.get_doc(defaults)

    # ---------- tests (using real conversion helpers) ----------

    def test_pair_rule_both_empty_is_ok(self):
        # both ref fields empty → ok
        doc = self._new_doc(ref_letter="", ref_date_djalali="")
        doc.insert()

    def test_pair_rule_only_ref_letter_raises(self):
        # only letter → should raise per controller
        doc = self._new_doc(ref_letter="A-123", ref_date_djalali="")
        with self.assertRaises(ValidationError):
            doc.insert()

    def test_pair_rule_only_ref_date_raises(self):
        # only date → should raise per controller
        doc = self._new_doc(ref_letter="", ref_date_djalali="1404/06/25")
        with self.assertRaises(ValidationError):
            doc.insert()

    def test_jalali_to_gregorian_and_back_on_validate(self):
        # pair rule satisfied: provide BOTH values
        doc = self._new_doc(ref_letter="A-123", ref_date_djalali="1404/06/25")
        doc.insert()
        # your converter maps 1404/06/25 <-> 2025-09-15
        self.assertEqual(doc.ref_date, "2025-09-16")
        self.assertEqual(doc.ref_date_djalali, "1404/06/25")

    def test_gregorian_to_jalali_when_both_present(self):
        # to exercise reverse conversion with real module, set BOTH so validate accepts it
        doc = self._new_doc(ref_letter="A-123", ref_date="2025-09-16", ref_date_djalali="1404/06/25")
        doc.insert()
        self.assertEqual(doc.ref_date_djalali, "1404/06/25")

    def test_prompt_required_for_prompt_required_types(self):
        # use an allowed type that DOES require prompt according to your controller (e.g. "اطلاعیه")
        bad = self._new_doc(letter_type="اطلاعیه", prompt="")
        with self.assertRaises(ValidationError):
            bad.insert()

        ok = self._new_doc(letter_type="اطلاعیه", prompt="توضیح تست")
        ok.insert()

    def test_onload_sets_jalali_from_saved_gregorian(self):
        # pair rule satisfied (both given). controller will normalize them; later onload should mirror.
        doc = self._new_doc(ref_letter="A-123", ref_date="2025-09-16", ref_date_djalali="1404/06/25")
        doc.insert()
        # simulate form load (clear mirror then call onload)
        frappe.db.set_value(DOCTYPE_NAME, doc.name, "ref_date_djalali", "")
        doc.reload()
        doc.onload()
        self.assertEqual(doc.ref_date_djalali, "1404/06/25")
