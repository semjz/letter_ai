# apps/letter_ai/letter_ai/setup.py
import frappe

DOCTYPE = "letter_ai"

# Only the two actions you use in this 3-state model
ACTIONS = ["Submit", "Approve"]
ROLES   = ["Employee", "HR Manager"]

STATES  = [
    {"name": "Draft",             "style": "Primary"},
    {"name": "Pending Approval",  "style": "Warning"},
    {"name": "Approved",          "style": "Success"},
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
    # Employee: read, write, create
    emp = _get_or_create_docperm(DOCTYPE, "Employee", 0)
    emp.read = emp.write = emp.create = 1
    emp.save(ignore_permissions=True)

    # HR Manager: read, write, create, submit (needed for Approve transition which keeps docstatus=1)
    hr = _get_or_create_docperm(DOCTYPE, "HR Manager", 0)
    hr.read = hr.write = hr.create = 1
    hr.submit = 1
    hr.save(ignore_permissions=True)

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

    # Draft(0) --Submit--> Pending Approval(1) --Approve--> Approved(1)
    wf.set("states", [
        {"state": "Draft",            "doc_status": 0, "allow_edit": "Employee"},
        {"state": "Pending Approval", "doc_status": 0, "allow_edit": "HR Manager"},
        {"state": "Approved",         "doc_status": 1, "allow_edit": "HR Manager"},
    ])

    wf.set("transitions", [
        {"state": "Draft",            "action": "Submit",  "next_state": "Pending Approval", "allowed": "Employee"},
        {"state": "Draft",            "action": "Submit",  "next_state": "Pending Approval", "allowed": "HR Manager"},
        {"state": "Pending Approval", "action": "Approve", "next_state": "Approved",         "allowed": "HR Manager"},
    ])

    wf.save(ignore_permissions=True)
    frappe.db.commit()
