# apps/letter_ai/letter_ai/letter_ai/doctype/letter_ai/tests_shared.py
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

DOCTYPE_NAME = "letter_ai"   # use the exact DocType title in Desk

def ensure_company():
    name = frappe.db.get_value("Company", {}, "name")
    if name: return name
    return frappe.get_doc({
        "doctype": "Company",
        "company_name": "Test Company",
        "abbr": "TC",
        "default_currency": "USD",
        "country": "United States",
    }).insert(ignore_permissions=True).name

def ensure_employee(company):
    name = frappe.db.get_value("Employee", {}, "name")
    if name: return name
    return frappe.get_doc({
        "doctype": "Employee",
        "employee_name": "Test Employee",
        "company": company,
        "date_of_joining": nowdate(),
    }).insert(ignore_permissions=True).name

def new_letter(**overrides):
    defaults = dict(
        doctype=DOCTYPE_NAME,
        letter_name="LT-" + frappe.generate_hash(length=8),
        letter_type="معرفی",
        tone_of_writing="اداری",
        sender=frappe.db.get_value("Employee", {}, "name"),
        recipient_company=frappe.db.get_value("Company", {}, "name"),
        prompt="",
        ref_letter="",
        ref_date="",
        ref_date_djalali="",
        generated_letter="",
    )
    defaults.update(overrides)
    return frappe.get_doc(defaults)

# (optional) import your workflow installer if you want it ready for every test
try:
    from letter_ai.setup import ensure_letter_ai_workflow
except Exception:
    ensure_letter_ai_workflow = None

class LetterAITestBase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.db.rollback()
        cls.company = ensure_company()
        cls.employee = ensure_employee(cls.company)
        if ensure_letter_ai_workflow:
            ensure_letter_ai_workflow()  # idempotent upsert version recommended

    def setUp(self):
        frappe.db.rollback()

    # handy helper available to subclasses
    def make_letter(self, **kw):
        kw.setdefault("sender", self.employee)
        kw.setdefault("recipient_company", self.company)
        doc = new_letter(**kw)
        return doc
