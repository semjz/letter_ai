// Copyright (c) 2025, saman and contributors
// For license information, please see license.txt

frappe.ui.form.on('letter_ai', {
  refresh(frm) {
    frm.toggle_display('generated_letter', !!frm.doc.generated_letter);

    // Add Generate Letter Button
    addGenerateLetterButton(frm);

    // Add Regenerate with Edits Button if the letter is already generated
    if (frm.doc.generated_letter) {
      addRegenerateButton(frm);
    }

    // Add Export as PDF Button if the letter is already generated
    if (frm.doc.generated_letter) {
      addExportPdfButton(frm);
    }
  }
});

// Function to add "Generate Letter" Button
function addGenerateLetterButton(frm) {
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
    })
    .then(() => {
      frm.reload_doc()
        .then(() => {
          frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
        });
    });
  });
}

// Function to add "Regenerate with Edits" Button
function addRegenerateButton(frm) {
  frm.add_custom_button(__('Regenerate with Edits'), () => {
    if (frm.is_dirty()) {
      frappe.msgprint(__('Please save first.'));
      return;
    }

    frappe.call({
      method: 'letter_ai.api.letter_ai.edit_letter',
      args: { docname: frm.doc.name },
      freeze: true,
      freeze_message: __('Regenerating letter with edits… This may take a few seconds.')
    })
    .then(() => {
      frm.reload_doc()
        .then(() => {
          frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
        });
    });
  });
}
