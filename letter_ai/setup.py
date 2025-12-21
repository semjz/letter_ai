# apps/letter_ai/letter_ai/setup.py
import frappe

DOCTYPE = "letter_ai"

ACTIONS = ["Submit", "Approve"]
ROLES   = ["HR Manager", "Managing Director", "CEO"]  # Employee removed

STATES  = [
    {"name": "Draft",                "style": "Primary"},
    {"name": "Pending MD Approval",  "style": "Warning"},
    {"name": "Pending CEO Approval", "style": "Warning"},
    {"name": "Approved",             "style": "Success"},
]

def _get_or_create_docperm(doctype: str, role: str, permlevel: int = 0):
    name = frappe.db.get_value(
        "DocPerm", {"parent": doctype, "role": role, "permlevel": permlevel}, "name"
    )
    if name:
        return frappe.get_doc("DocPerm", name)
    dp = frappe.get_doc({
        "doctype": "DocPerm",
        "parenttype": "DocType",
        "parentfield": "permissions",
        "parent": doctype,
        "role": role,
        "permlevel": permlevel,
    })
    dp.insert(ignore_permissions=True)
    return dp

def _ensure_perms():
    # HR Manager: only own docs; can create; no submit
    hr = _get_or_create_docperm(DOCTYPE, "HR Manager", 0)
    hr.read = 1; hr.write = 1; hr.create = 1
    hr.if_owner = 1
    hr.submit = 0
    hr.save(ignore_permissions=True)

    # Managing Director: can read/write all; can create; no submit (not final approver)
    md = _get_or_create_docperm(DOCTYPE, "Managing Director", 0)
    md.read = 1; md.write = 1; md.create = 1
    md.submit = 0
    md.if_owner = 0
    md.save(ignore_permissions=True)

    # CEO: can read/write all; can create; has submit (final step makes docstatus=1)
    ceo = _get_or_create_docperm(DOCTYPE, "CEO", 0)
    ceo.read = 1; ceo.write = 1; ceo.create = 1
    ceo.submit = 1
    ceo.if_owner = 0
    ceo.save(ignore_permissions=True)

    frappe.clear_cache(doctype=DOCTYPE)


def _ensure_action(name: str):
    if not frappe.db.exists("Workflow Action Master", name):
        frappe.get_doc({
            "doctype": "Workflow Action Master",
            "workflow_action_name": name,
        }).insert(ignore_permissions=True)

def _ensure_role(name: str):
    if not frappe.db.exists("Role", name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": name,
        }).insert(ignore_permissions=True)

def _ensure_state(name: str, style: str = ""):
    if not frappe.db.exists("Workflow State", name):
        frappe.get_doc({
            "doctype": "Workflow State",
            "workflow_state_name": name,
            "style": style or "Grey",
        }).insert(ignore_permissions=True)

def _ensure_workflow_state_field():
    meta = frappe.get_meta(DOCTYPE)
    if not any(df.fieldname == "workflow_state" for df in meta.fields):
        if not frappe.db.exists("Custom Field", f"{DOCTYPE}-workflow_state"):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": DOCTYPE,
                "label": "Workflow State",
                "fieldname": "workflow_state",
                "fieldtype": "Data",
                "read_only": 1,
                "no_copy": 1,
            }).insert(ignore_permissions=True)

def ensure_letter_ai_workflow():
    # Ensure deps
    for a in ACTIONS: _ensure_action(a)
    for r in ROLES:   _ensure_role(r)
    for s in STATES:  _ensure_state(s["name"], s["style"])
    _ensure_perms()
    _ensure_workflow_state_field()

    # Deactivate any other active workflows for this DocType
    for name in frappe.get_all("Workflow", filters={"document_type": DOCTYPE, "is_active": 1}, pluck="name"):
        if name != "Letter AI Workflow":
            frappe.db.set_value("Workflow", name, "is_active", 0)

    # Upsert this workflow
    if frappe.db.exists("Workflow", "Letter AI Workflow"):
        wf = frappe.get_doc("Workflow", "Letter AI Workflow")
    else:
        wf = frappe.new_doc("Workflow")
        wf.workflow_name = "Letter AI Workflow"
        wf.document_type = DOCTYPE

    wf.is_active = 1
    wf.workflow_state_field = "workflow_state"

    # Who may edit in each state (editing still needs DocPerm write)
    wf.set("states", [
        {"state": "Draft",                "doc_status": 0, "allow_edit": "HR Manager"},
        {"state": "Pending MD Approval",  "doc_status": 0, "allow_edit": "Managing Director"},
        {"state": "Pending CEO Approval", "doc_status": 0, "allow_edit": "CEO"},
        {"state": "Approved",             "doc_status": 1, "allow_edit": "CEO"},  # or leave empty to make read-only
    ])

    wf.set("transitions", [
        # HR creates & submits own letter -> MD step
        {"state": "Draft", "action": "Submit",  "next_state": "Pending MD Approval",  "allowed": "HR Manager"},

        # MD can start their own letter, or pick up a Draft -> MD step
        {"state": "Draft", "action": "Submit",  "next_state": "Pending MD Approval",  "allowed": "Managing Director"},

        # CEO can start and SKIP MD (fast-track) — Scenario A
        {"state": "Draft", "action": "Submit",  "next_state": "Pending CEO Approval", "allowed": "CEO"},

        # Or CEO can take the MD step too (do both approvals) — Scenario B (step 1 of 2)
        {"state": "Draft", "action": "Submit",  "next_state": "Pending MD Approval",  "allowed": "CEO"},

        # MD approves -> CEO step (normal route)
        {"state": "Pending MD Approval", "action": "Approve", "next_state": "Pending CEO Approval", "allowed": "Managing Director"},

        # CEO is allowed to perform the MD approval step as well — Scenario B (step 2 of 2)
        {"state": "Pending MD Approval", "action": "Approve", "next_state": "Pending CEO Approval", "allowed": "CEO"},

        # Final: CEO approves -> Approved (doc_status=1; requires CEO.submit=1)
        {"state": "Pending CEO Approval", "action": "Approve", "next_state": "Approved", "allowed": "CEO"},

        # (Optional) Ultra fast-track if you want CEO to jump straight from MD step to Approved in one click:
        # {"state": "Pending MD Approval", "action": "Approve", "next_state": "Approved", "allowed": "CEO"},
    ])


    wf.save(ignore_permissions=True)
    frappe.db.commit()
