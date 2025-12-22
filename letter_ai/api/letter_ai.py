import os
import re
import frappe
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from frappe import _
from frappe.model.workflow import get_workflow

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

TEMPLATE_PATH = os.path.join(frappe.get_app_path("letter_ai"), "templates", "letters")
env = Environment(
    loader=FileSystemLoader(TEMPLATE_PATH),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

# ---- Role names (change only if your roles are named differently) ----
ROLE_CEO = "CEO"
ROLE_LETTER = "Letter Generator"


def _can_generate(user: str) -> bool:
    roles = frappe.get_roles(user)
    return (ROLE_CEO in roles) or (ROLE_LETTER in roles)


def _get_employee_for_user(user: str):
    emp_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return frappe.get_doc("Employee", emp_name) if emp_name else None


def _resolve_sender_designation(user: str) -> str:
    """
    Strict rule:
      1) If user has an Employee -> use Employee.designation (fallback 'employee')
      2) Else if user has CEO role -> 'CEO'
      3) Else -> ''
    """
    emp = _get_employee_for_user(user)
    if emp:
        return (emp.designation or "").strip() or "employee"

    if ROLE_CEO in frappe.get_roles(user):
        return "CEO"

    return ""


def _sj(v):  # safe strip
    return (v or "").strip()

def _parse_runtime(runtime_values) -> dict:
    if not runtime_values:
        return {}
    if isinstance(runtime_values, dict):
        return runtime_values
    try:
        return frappe.parse_json(runtime_values) or {}
    except Exception:
        logger.exception("Failed to parse runtime_values; using empty dict")
        return {}

def _render(template_file: str, data: dict) -> str:
    return env.get_template(template_file).render(**data)

def _render_and_save(docname: str, template_file: str, data: dict) -> str:
    letter = _render(template_file, data)
    doc = frappe.get_doc("letter_ai", docname)
    doc.reload()
    doc.db_set("generated_letter", letter, notify=True, commit=True)
    return letter

def _get_current_wf_state(doc):
    doc.reload()
    wf = get_workflow(doc.doctype)
    if not wf or not wf.workflow_state_field:
        return None
    return doc.get(wf.workflow_state_field)

def _assert_can_generate_soft(doc):
    if doc.docstatus != 0:
        return False, _("Only allowed for Draft documents.")

    allowed_states = {"Draft"}  # keep in sync with client
    wf_state = _get_current_wf_state(doc)
    logger.info("wf_state=%s", wf_state)
    if wf_state and wf_state not in allowed_states:
        return False, _("Not allowed in workflow state: {0}").format(wf_state)
    return True, None

# ---------------- Registry for template-backed letters ----------------
# Each entry defines:
# - template: Jinja template file
# - fields:   { persian_placeholder: "incoming_payload_key" }
# - required: a subset of payload keys that must be present (optional)
TEMPLATE_REGISTRY = {
    "bargiri": {
        "template": "bargiri_letter.j2",
        "fields": {
            "طرف_قرارداد": "contract_party",
            "مرجع": "authority",
            "نوع_پسماند": "waste_type",
            "دوره": "period",
            "تاریخ_شروع": "start_date",
            "تاریخ_پایان": "end_date",
        },
        # "required": {"contract_party", "waste_type"}  # uncomment if you want validation
    },
    "govahi": {
        "template": "govahi_letter.j2",
        "fields": {
            "عنوان_جنسیتی": "gender",
            "نام": "name",
            "نام_پدر": "father_name",
            "کد_ملی": "national_code",
            "مدرک": "study_level",
            "رشته": "major",
            "گرایش": "specialize",
            "دانشگاه": "uni",
            "از_تاریخ1": "from_date1",
            "تا_تاریخ1": "to_date1",
            "از_تاریخ2": "from_date2",
            "شرکت": "company",
            "سمت": "post",
            "مرجع": "to",
        },
    },
    "moarefi": {
        "template": "moarefi_letter.j2",
        "fields": {
            "عنوان_جنسیتی": "gender",
            "نام": "name",
            "کد_ملی": "national_code",
            "امور": "duty",
        },
    },
    "gozaresh": {
        "template": "gozaresh_letter.j2",
        "fields": {
            "نام_گزارش": "report_name",
            "تاریخ_گزارش": "report_date",
        },
    },
}

def _build_context(template_key: str, payload: dict) -> tuple[str, dict]:
    cfg = TEMPLATE_REGISTRY.get(template_key)
    if not cfg:
        frappe.throw(f"Unknown template key: {template_key}")
    fields = cfg["fields"]
    data = { persian: _sj(payload.get(in_key)) for persian, in_key in fields.items() }

    # Optional: enforce required payload keys if you want strictness
    req = set(cfg.get("required", []))
    if req:
        missing = [k for k in req if _sj(payload.get(k)) == ""]
        if missing:
            frappe.throw(f"Missing required fields: {', '.join(missing)}")

    return cfg["template"], data

@frappe.whitelist()
def generate_from_template(docname: str, template_key: str, runtime_values=None) -> str:
    """
    One generic endpoint for all simple template-backed letters.
    template_key must be one of TEMPLATE_REGISTRY keys: bargiri|govahi|moarefi|gozaresh
    """
    doc = frappe.get_doc("letter_ai", docname)
    ok, why = _assert_can_generate_soft(doc)
    if not ok:
        return {"status": "blocked", "message": why}
    payload = _parse_runtime(runtime_values)
    template_file, data = _build_context(template_key, payload)
    return _render_and_save(docname, template_file, data)


@frappe.whitelist()
def generate_letter(docname: str):
    user = frappe.session.user

    # Role gate for generation
    if not _can_generate(user):
        return {"status": "blocked", "message": _("Not allowed to generate letters.")}

    # Load document
    doc = frappe.get_doc("letter_ai", docname)

    # Your existing soft authorization gate
    ok, why = _assert_can_generate_soft(doc)
    # logger.info("ok=%s, why=%s", ok, why)
    if not ok:
        return {"status": "blocked", "message": why}

    doc.reload()

    # Safety net (company should be set by controller before_insert)
    if not getattr(doc, "company", None):
        return {"status": "blocked", "message": _("Company is missing on the document.")}

    sender_designation = _resolve_sender_designation(user)

    prompt = f"""
type:{doc.letter_type}
tone:{doc.tone_of_writing}
company:{doc.company}
sender_designation:{sender_designation}

{doc.prompt}
"""

    api_key = frappe.get_conf().openai_api_key
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {
                "role": "system",
                "content": "You generate a letter title and the main body ONLY. Do NOT include date, recipient/sender blocks, greetings, or signatures.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    content = remove_placeholders(response.choices[0].message.content)
    doc.db_set("generated_letter", content, notify=True, commit=True)
    return content

@frappe.whitelist()
def edit_letter(docname, type, tone, rec):
    api_key = frappe.get_conf().openai_api_key
    client = OpenAI(api_key=api_key)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    ok, why = _assert_can_generate_soft(doc)
    logger.info("ok=%s, why=%s", ok, why)
    if not ok:
        return {"status": "blocked", "message": why}
    doc.reload()

    new_type, new_tone, new_rec = "", "", ""

    if doc.letter_type != type:
        type = f"new letter type is {type}"
    if doc.tone_of_writing != tone:
        type = f"new letter tone is {tone}"
    if doc.recipient_company is not rec:
        new_rec = f"new receiver company is {rec}"

    prompt = f"""Apply {doc.prompt}, {new_type} {new_tone} {new_rec} changes to this letter:
                 {doc.generated_letter}
                 Only return the edited letter's main text as the response — no greeting, no signature.
              """


    # logger.info("edit letter" + prompt)
    response = client.chat.completions.create(
     model="ft:gpt-4.1-mini-2025-04-14:caspian-industry-era:letter-ai-draft3:C6GPtfne",
       messages=[
            {"role": "system", "content": "You are editing the provided text according to the user's instructions. Keep the style consistent and return only the main body, no greeting or closing."},
            {"role": "assistant", "content": doc.generated_letter},
            {"role": "user", "content": prompt}
       ]
    )
    content = remove_placeholders(response.choices[0].message.content)
    # logger.info(f"edit letter API response: {response}")
    doc.db_set("generated_letter", content, notify=True, commit=True)
    return content
def remove_placeholders(text):
    return re.sub(r'\[.*?\]', '', text).strip()