# Copyright (c) 2025, saman and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from .djalali_georgian_conversion import (
    parse_jalali_to_greg_iso,     # '1404/06/25' -> '2025-09-15'
    greg_iso_to_jalali_str        # '2025-09-15' -> '1404/06/25'
)

# ----------------------------
# Business rules / constants
# ----------------------------

NO_PROMPT_TYPES = {"گزارش", "معرفی", "بارگیری", "گواهی اشتغال به کار"}

ROLE_CEO = "CEO"
ROLE_LETTER = "Letter Generator"   # rename if you prefer


# ----------------------------
# Small utilities
# ----------------------------

def _strip(val) -> str:
    return (val or "").strip()

def _has_any_text(*vals) -> bool:
    return any(_strip(v) for v in vals)

def _to_iso_date(val) -> str:
    """
    Normalize a python date/datetime or string into ISO yyyy-mm-dd (string).
    """
    if hasattr(val, "isoformat"):  # date or datetime
        # datetime has .date(), date does not
        return val.date().isoformat() if hasattr(val, "date") else val.isoformat()
    return _strip(val)

def _current_user() -> str:
    return frappe.session.user

def _user_roles(user: str) -> list[str]:
    return frappe.get_roles(user)

def _has_role(user: str, role: str) -> bool:
    return role in _user_roles(user)

def _is_ceo(user: str) -> bool:
    return _has_role(user, ROLE_CEO)

def _can_create_letter(user: str) -> bool:
    """
    Your policy: only CEO or Letter Generator can create/insert letter_ai.
    """
    roles = _user_roles(user)
    return (ROLE_CEO in roles) or (ROLE_LETTER in roles)

def _get_employee_company(user: str) -> str | None:
    """
    Employee.user_id must link to User for this to work.
    """
    return frappe.db.get_value("Employee", {"user_id": user}, "company")


# ----------------------------
# Validations (checks only)
# ----------------------------

def _validate_ref_fields(doc: Document) -> None:
    """
    rule: ref_letter and ref_date/ref_date_djalali must be filled together
    """
    doc.ref_letter = _strip(getattr(doc, "ref_letter", ""))

    has_ref = bool(doc.ref_letter)
    has_any_date = _has_any_text(getattr(doc, "ref_date_djalali", None), getattr(doc, "ref_date", None))

    if has_ref ^ has_any_date:
        frappe.throw("لطفا هر دو فیلد «نامه مرجع» و «تاریخ مرجع» را با هم پر کنید.")

def _validate_prompt_requirement(doc: Document) -> None:
    if doc.letter_type not in NO_PROMPT_TYPES and not _strip(getattr(doc, "prompt", "")):
        frappe.throw(_("Prompt is required for letter type: {0}").format(doc.letter_type))

def _validate_create_permission(doc: Document, user: str) -> None:
    """
    Enforce who is allowed to create new letters at all.
    This runs in validate so it blocks early (before DB insert).
    """
    if doc.is_new() and not _can_create_letter(user):
        frappe.throw(_("You are not allowed to create letters."))

def _prevent_company_change_after_insert(doc: Document, user: str) -> None:
    """
    Optional invariant: non-CEO cannot change company after creation.
    If you want to lock for everyone, remove CEO exception.
    """
    if doc.is_new():
        return
    if doc.has_value_changed("company") and not _is_ceo(user):
        frappe.throw(_("Not allowed to change company."))


# ----------------------------
# Mutations / normalization
# ----------------------------

def _ensure_workflow_default(doc: Document) -> None:
    # Ensure workflow starts at Draft so transitions are visible
    if not getattr(doc, "workflow_state", None):
        doc.workflow_state = "Draft"

def _assign_company_on_insert(doc: Document, user: str) -> None:
    """
    Your design:
    - company is mandatory on the doc
    - non-CEO gets company from Employee.company
    - CEO must choose company manually (no Employee record needed)
    """
    if not doc.is_new():
        return

    if _is_ceo(user):
        if not _strip(getattr(doc, "company", "")):
            frappe.throw(_("Company is required for CEO. Please choose a company."))
        return

    # Non-CEO: force company from Employee
    emp_company = _get_employee_company(user)
    if not emp_company:
        frappe.throw(_("Only employees can create letters (no Employee linked to this user)."))
    doc.company = emp_company

def _normalize_ref_date_fields(doc: Document) -> None:
    """
    Keeps ref_date (ISO) and ref_date_djalali in sync.
    """
    jalali_text = _strip(getattr(doc, "ref_date_djalali", ""))

    if jalali_text:
        iso = parse_jalali_to_greg_iso(jalali_text)
        doc.ref_date = iso
        doc.ref_date_djalali = greg_iso_to_jalali_str(iso)
        return

    if getattr(doc, "ref_date", None):
        iso = _to_iso_date(doc.ref_date)
        doc.ref_date = iso
        doc.ref_date_djalali = greg_iso_to_jalali_str(iso)
        return

    doc.ref_date = ""
    doc.ref_date_djalali = ""

def _mirror_ref_date_for_ui(doc: Document) -> None:
    """
    Read-time mirror for UI convenience (onload).
    """
    if doc.get("ref_date"):
        iso = _to_iso_date(doc.ref_date)
        doc.ref_date_djalali = greg_iso_to_jalali_str(iso)


# ----------------------------
# Document class
# ----------------------------

class letter_ai(Document):
    def validate(self):
        user = _current_user()

        # Checks only
        _validate_create_permission(self, user)
        _prevent_company_change_after_insert(self, user)

        _validate_ref_fields(self)
        _validate_prompt_requirement(self)

    def before_insert(self):
        user = _current_user()

        # Mutations only (new doc)
        _ensure_workflow_default(self)
        _assign_company_on_insert(self, user)

    def before_save(self):
        # Mutations/normalization (insert + update)
        _normalize_ref_date_fields(self)

    def onload(self):
        # Read-time mirror for UI convenience
        _mirror_ref_date_for_ui(self)
