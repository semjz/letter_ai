// Copyright (c) 2025, saman and contributors
// For license information, please see license.txt

frappe.ui.form.on("letter_ai", {
 	refresh(frm) {
         if (!frm.doc.generated_letter) {
           frm.add_custom_button("Generate Letter", () => {
            frappe.call({
            method: "letter_ai.api.letter_ai.generate_letter",
            args: { docname: frm.doc.name },
            freeze: true,
            freeze_message: "Generating AI letter…",
            callback: () => frm.reload_doc()
          });
        });
       }
     },
});
