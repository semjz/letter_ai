import os
import re
import frappe
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

TEMPLATE_PATH = os.path.join(frappe.get_app_path("letter_ai"), "templates", "letters")
env = Environment(
    loader=FileSystemLoader(TEMPLATE_PATH),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

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
    payload = _parse_runtime(runtime_values)
    logger.info("generate_from_template key=%s payload=%s", template_key, payload)
    template_file, data = _build_context(template_key, payload)
    return _render_and_save(docname, template_file, data)

@frappe.whitelist()
def generate_bargiri_letter(docname, runtime_values):
    return generate_from_template(docname, "bargiri", runtime_values)

@frappe.whitelist()
def generate_govahi_letter(docname, runtime_values):
    return generate_from_template(docname, "govahi", runtime_values)

@frappe.whitelist()
def generate_moarefi_letter(docname, runtime_values):
    return generate_from_template(docname, "moarefi", runtime_values)

@frappe.whitelist()
def generate_gozaresh_letter(docname, runtime_values):
    return generate_from_template(docname, "gozaresh", runtime_values)


@frappe.whitelist()
def generate_letter(docname):
    api_key = frappe.get_conf().openai_api_key
    client = OpenAI(api_key=api_key)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    doc.reload()

     # Fetch Employee (Sender) Details
    sender = frappe.get_doc("Employee", doc.sender)  # Assuming doc.sender is the employee link
    sender_name = sender.employee_name
    sender_designation = sender.designation
    sender_company = sender.company  # Company the employee works for
    sender_address = sender.current_address or "Address not provided"  # Default if no address provided
    sender_email = sender.personal_email

    # Fetch Company (Recipient) Details
    recipient_company = frappe.get_doc("Company", doc.recipient_company)  # Assuming doc.receiver is the company link
    recipient_company_name = recipient_company.company_name
    recipient_company_owner = recipient_company.owner
    recipient_company_description = recipient_company.company_description or "No description available"
    # Constructing the prompt with dynamic data from both Employee and Company
    prompt = f"""
      type:{doc.letter_type}
      tone:{doc.tone_of_writing}
      {doc.prompt}

    """
    logger.info("generate letter" + prompt)
    response = client.chat.completions.create(
     model="gpt-4.1-mini-2025-04-14",
     messages=[
        {"role": "system", "content": "You generate a letter title and the main body ONLY. Do NOT include date, recipient/sender blocks, greetings, or signatures."},
        {"role": "user", "content": prompt}
     ]
    )
    content = remove_placeholders(response.choices[0].message.content)
    logger.info(f"generate letter API response: {response}")
    doc.db_set("generated_letter", content, notify=True, commit=True)
    return content

@frappe.whitelist()
def edit_letter(docname, type, tone, rec):
    api_key = frappe.get_conf().openai_api_key
    client = OpenAI(api_key=api_key)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
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


    logger.info("edit letter" + prompt)
    response = client.chat.completions.create(
     model="ft:gpt-4.1-mini-2025-04-14:caspian-industry-era:letter-ai-draft3:C6GPtfne",
       messages=[
            {"role": "system", "content": "You are editing the provided text according to the user's instructions. Keep the style consistent and return only the main body, no greeting or closing."},
            {"role": "assistant", "content": doc.generated_letter},
            {"role": "user", "content": prompt}
       ]
    )
    content = remove_placeholders(response.choices[0].message.content)
    logger.info(f"edit letter API response: {response}")
    doc.db_set("generated_letter", content, notify=True, commit=True)
    return content
def remove_placeholders(text):
    return re.sub(r'\[.*?\]', '', text).strip()