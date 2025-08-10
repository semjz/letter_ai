// Copyright (c) 2025, saman and contributors
// For license information, please see license.txt

frappe.ui.form.on('letter_ai', {
  refresh(frm) {
    frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
      frm.add_custom_button(__('Generate Letter'), () => {
        if (frm.is_dirty()) {
          frappe.msgprint(__('Please save first.'));
          return;
        }
        frappe.call({
          method: 'letter_ai.api.letter_ai.generate_letter',
          args: { docname: frm.doc.name },
          freeze: true,
          freeze_message: __('Generating letter… This may take a few seconds.')
        }).then(() => {
          frm.reload_doc().then(() => {
            frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
          });
        });
      });
  }
});

