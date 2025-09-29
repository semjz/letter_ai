# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

# Import your API module (adjust if your file lives somewhere else)
from letter_ai.api import letter_ai as api_mod

DOCTYPE_NAME = "letter_ai"  # must match your DocType name exactly


class TestLetterAPIs(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.db.rollback()

        # Ensure the templates folder exists and create minimal templates
        cls.tpl_root = os.path.join(
            frappe.get_app_path("letter_ai"), "templates", "letters"
        )
        os.makedirs(cls.tpl_root, exist_ok=True)

        # Write tiny templates used by the API functions
        cls._write_template("bargiri_letter.j2", "BARGIRI {{ طرف_قرارداد }} {{ مرجع }} {{ نوع_پسماند }} {{ دوره }} {{ تاریخ_شروع }} {{ تاریخ_پایان }}")
        cls._write_template("govahi_letter.j2", "GOVAHI {{ عنوان_جنسیتی }} {{ نام }} {{ نام_پدر }} {{ کد_ملی }} {{ مدرک }} {{ رشته }} {{ گرایش }} {{ دانشگاه }} {{ از_تاریخ1 }} {{ تا_تاریخ1 }} {{ از_تاریخ2 }} {{ شرکت }} {{ سمت }} {{ مرجع }}")
        cls._write_template("moarefi_letter.j2", "MOAREFI {{ عنوان_جنسیتی }} {{ نام }} {{ کد_ملی }} {{ امور }}")
        cls._write_template("gozaresh_letter.j2", "GOZARESH {{ نام_گزارش }} {{ تاریخ_گزارش }}")

    @classmethod
    def _write_template(cls, filename: str, content: str):
        path = os.path.join(cls.tpl_root, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def setUp(self):
        frappe.db.rollback()

        # Ensure minimal Company
        self.company = frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.company = frappe.get_doc({
                "doctype": "Company",
                "company_name": "Test Company",
                "abbr": "TC",
                "default_currency": "USD",
                "country": "United States",
            }).insert(ignore_permissions=True).name

        # Ensure minimal Employee
        self.employee = frappe.db.get_value("Employee", {}, "name")
        if not self.employee:
            self.employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": "Test Employee",
                "company": self.company,
                "date_of_joining": nowdate(),
            }).insert(ignore_permissions=True).name

        # Create a base letter_ai doc
        self.doc = frappe.get_doc({
            "doctype": DOCTYPE_NAME,
            "letter_name": "LT-" + frappe.generate_hash(length=6),
            "letter_type": "معرفی",             # allowed non-prompt type
            "tone_of_writing": "اداری",
            "sender": self.employee,
            "recipient_company": self.company,
            "prompt": "پرامپت تست",
        }).insert(ignore_permissions=True)

    # ---------------- template-based APIs ----------------

    def test_generate_bargiri_letter(self):
        payload = {
            "contract_party": "ACME",
            "authority": "شهرداری",
            "waste_type": "خشک",
            "period": "1404-Q1",
            "start_date": "1404/01/01",
            "end_date": "1404/01/31",
        }
        result = api_mod.generate_from_template(self.doc.name, "bargiri",json.dumps(payload))
        self.doc.reload()
        self.assertIn("BARGIRI ACME شهرداری خشک 1404-Q1 1404/01/01 1404/01/31", result)
        self.assertEqual(self.doc.generated_letter, result)

    def test_generate_govahi_letter(self):
        payload = {
            "gender": "خانم",
            "name": "الهام",
            "father_name": "رضا",
            "national_code": "0012345678",
            "study_level": "کارشناسی",
            "major": "نرم‌افزار",
            "specialize": "هوش مصنوعی",
            "uni": "دانشگاه تهران",
            "from_date1": "1402/01/01",
            "to_date1": "1403/01/01",
            "from_date2": "1403/02/01",
            "company": "شرکت نمونه",
            "post": "کارشناس",
            "to": "سازمان تامین اجتماعی",
        }
        result = api_mod.generate_from_template(self.doc.name, "govahi", json.dumps(payload))
        self.doc.reload()
        self.assertIn("GOVAHI خانم الهام رضا 0012345678 کارشناسی نرم‌افزار هوش مصنوعی دانشگاه تهران 1402/01/01 1403/01/01 1403/02/01 شرکت نمونه کارشناس سازمان تامین اجتماعی", result)
        self.assertEqual(self.doc.generated_letter, result)

    def test_generate_moarefi_letter(self):
        payload = {
            "gender": "آقا",
            "name": "علی",
            "national_code": "1234567890",
            "duty": "امور اداری",
        }
        result = api_mod.generate_from_template(self.doc.name, "moarefi", json.dumps(payload))
        self.doc.reload()
        self.assertIn("MOAREFI آقا علی 1234567890 امور اداری", result)
        self.assertEqual(self.doc.generated_letter, result)

    def test_generate_gozaresh_letter(self):
        payload = {
            "report_name": "گزارش عملکرد",
            "report_date": "1404/06/31",
        }
        result = api_mod.generate_from_template(self.doc.name, "gozaresh",json.dumps(payload))
        self.doc.reload()
        self.assertIn("GOZARESH گزارش عملکرد 1404/06/31", result)
        self.assertEqual(self.doc.generated_letter, result)

    # ---------------- OpenAI-backed APIs (stubbed) ----------------

    def _fake_openai_choice(self, text: str):
        # Mimic OpenAI response object shape used by your code
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=text)
                )
            ]
        )

    @patch.object(api_mod, "OpenAI")
    def test_generate_letter_uses_openai_and_saves(self, OpenAI_cls):
        # Stub OpenAI to avoid network
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: self._fake_openai_choice("[TITLE] متن تولیدی [SIG]")
                )
            )
        )
        OpenAI_cls.return_value = fake_client

        result = api_mod.generate_letter(self.doc.name)
        self.doc.reload()
        # remove_placeholders strips [ ... ]
        self.assertEqual(result, "متن تولیدی")
        self.assertEqual(self.doc.generated_letter, "متن تولیدی")

    @patch.object(api_mod, "OpenAI")
    def test_edit_letter_applies_changes_and_saves(self, OpenAI_cls):
        # seed an initial generated letter
        self.doc.db_set("generated_letter", "متن اولیه", commit=True)

        # Fake OpenAI returns edited text with brackets to test cleanup
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: self._fake_openai_choice("متن ویرایش‌شده [FOOTER]")
                )
            )
        )
        OpenAI_cls.return_value = fake_client

        result = api_mod.edit_letter(self.doc.name, type="گزارش", tone="اداری", rec=self.company)
        self.doc.reload()
        self.assertEqual(result, "متن ویرایش‌شده")
        self.assertEqual(self.doc.generated_letter, "متن ویرایش‌شده")


if __name__ == "__main__":
    unittest.main()
