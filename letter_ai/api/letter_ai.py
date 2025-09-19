import frappe
import re
from openai import OpenAI
from datetime import date
from frappe.utils.pdf import get_pdf
from jinja2 import Environment, FileSystemLoader
import os


frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

TEMPLATE_PATH = os.path.join(frappe.get_app_path("letter_ai"), "templates", "letters")
env = Environment(
    loader=FileSystemLoader(TEMPLATE_PATH),
    autoescape=False,  # we don't want HTML escaping in plain text letters
    trim_blocks=True,
    lstrip_blocks=True
)

def render_template(file_name, data):
    tpl = env.get_template(file_name)
    return tpl.render(**data)


@frappe.whitelist()
def generate_bargiri_letter(docname, runtime_values):
    logger.info("runtime_values raw=%r type=%s", runtime_values, type(runtime_values).__name__)
    rv = frappe.parse_json(runtime_values) if runtime_values else {}
    if rv is None:
        rv = {}

    data = {
        "طرف_قرارداد": rv.get("contract_party").strip(),
        "مرجع": rv.get("authority").strip(),
        "نوع_پسماند": rv.get("waste_type").strip(),
        "دوره": rv.get("period").strip(),
        "تاریخ_شروع": rv.get("start_date", "").strip(),
        "تاریخ_پایان": rv.get("end_date", "").strip(),
    }


    letter = render_template("bargiri_letter.j2", data)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    doc.reload()
    doc.db_set("generated_letter", letter, notify=True, commit=True)

    return letter


@frappe.whitelist()
def generate_govahi_letter(docname, runtime_values):
    rv = frappe.parse_json(runtime_values) if runtime_values else {}
    if rv is None:
       rv = {}
    logger.info("runtime_values raw=%r type=%s",
    runtime_values, type(runtime_values).__name__)
    data = {
      "عنوان_جنسیتی": rv.get("gender").strip(),
      "نام":rv.get("name").strip(),
      "نام_پدر": rv.get("father_name").strip(),
      "کد_ملی": rv.get("national_code").strip(),
      "مدرک": rv.get("study_level").strip(),
      "رشته": rv.get("major").strip(),
      "گرایش": rv.get("specialize").strip(),
      "دانشگاه": rv.get("uni").strip(),
      "از_تاریخ1": rv.get("from_date1").strip(),
      "تا_تاریخ1": rv.get("to_date1", "").strip(),
      "از_تاریخ2": rv.get("from_date2", "").strip(),
      "شرکت": rv.get("company", "").strip(),
      "سمت": rv.get("post").strip(),
      "مرجع": rv.get("to").strip(),
    }

    letter = render_template("govahi_letter.j2", data)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    doc.reload()
    doc.db_set("generated_letter", letter, notify=True, commit=True)


@frappe.whitelist()
def generate_moarefi_letter(docname, runtime_values):
    logger.info("runtime_values raw=%r type=%s",
    runtime_values, type(runtime_values).__name__)
    rv = frappe.parse_json(runtime_values) if runtime_values else {}
    if rv is None:
        rv = {}
    data = {
            "عنوان_جنسیتی": rv.get("gender").strip(),
            "نام": rv.get("name").strip(),
            "کد_ملی": rv.get("national_code").strip(),
            "امور": rv.get("duty").strip()
           }

    letter = render_template("moarefi_letter.j2", data)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    doc.reload()
    doc.db_set("generated_letter", letter, notify=True, commit=True)

@frappe.whitelist()
def generate_gozaresh_letter(docname, runtime_values):
    rv = frappe.parse_json(runtime_values) if runtime_values else {}
    if rv is None:
        rv = {}
    data = {
            "نام_گزارش": rv.get("report_name").strip(),
            "تاریخ_گزارش": rv.get("report_date".strip())
	   }
    letter = render_template("gozaresh_letter.j2", data)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    doc.reload()
    doc.db_set("generated_letter", letter, notify=True, commit=True)

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
     model="ft:gpt-4.1-mini-2025-04-14:caspian-industry-era:letter-ai-draft3:C6GPtfne",
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
