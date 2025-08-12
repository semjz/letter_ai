import frappe
import re
from openai import OpenAI
from datetime import date
from frappe.utils.pdf import get_pdf

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

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
    generate only the final text of a rich farsi {doc.letter_type} letter  with {doc.tone_of_writing} tone using {doc.prompt}.

    Do not include any placeholders or instructions inside square brackets.
    If you don't know a detail, leave it blank or remove it completely.
    Start directly with the letter content and end with the closing statement.
    Do not add anything except the final letter text.
    Do not add any subject or anything before the main text.
    """
    logger.info("generate letter" + prompt)
    response = client.responses.create(
     model="gpt-4o-mini",
     input=prompt
    )
    content = remove_placeholders(response.output_text)
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

    prompt = f"""Apply {doc.prompt}, {new_type}, {new_tone} and {new_rec} changes to
		 this letter {doc.generated_letter} and only give me the edited letter text as response.
                 Do not include any placeholders or instructions inside square brackets.
                 If you don't know a detail, leave it blank or remove it completely.
                 Start directly with the letter content and end with the closing statement.
                 Do not add anything except the final letter text.
                 Do not add any subject or anything before the main text.
              """


    logger.info("edit letter" + prompt)
    response = client.responses.create(
     model="gpt-4o-mini",
     input=prompt
    )
    content = remove_placeholders(response.output_text)
    logger.info(f"edit letter API response: {response}")
    doc.db_set("generated_letter", content, notify=True, commit=True)
    return content

def remove_placeholders(text):
    return re.sub(r'\[.*?\]', '', text).strip()
