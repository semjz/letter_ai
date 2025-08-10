import frappe
from openai import OpenAI
from datetime import date

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

@frappe.whitelist()
def generate_letter(docname):
    api_key = frappe.get_conf().openai_api_key
    client = OpenAI(api_key=api_key)
    doc = frappe.get_doc(doctype="letter_ai", name=docname)
    doc.reload()
    logger.info(f"Fetched doc: {doc}")

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
    Write a {doc.letter_type} letter with {doc.tone_of_writing} tone in farsi with format below:
    sender:
    {sender_name}
    {sender_designation}
    {sender_company}
    {sender_address}
    {date.today()}
    {sender_email}

    receiver:
    {recipient_company_name}
    {recipient_company_owner}
    {recipient_company_description}

    create a good subject inspiring from {doc.prompt}

    and write the rest of the letter{doc.prompt} using all the data provided.
    """
    logger.info(prompt)
    response = client.responses.create(
     model="gpt-4o-mini",
     input=prompt
    )
    content = response.output_text
    logger.info(f"API response: {response}")
    doc.db_set("generated_letter", content, notify=True, commit=True)
    return content
