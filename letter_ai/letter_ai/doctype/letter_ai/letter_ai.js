// Copyright (c) 2025, saman and contributors
// For license information, please see license.txt

frappe.ui.form.on("letter_ai", {
  refresh(frm) {
    // Toggle letter preview visibility
    frm.toggle_display("generated_letter", !!frm.doc.generated_letter);

    // Action buttons
    addGenerateLetterButton(frm);
    if (frm.doc.generated_letter) {
      addRegenerateButton(frm);
    }

    toggle_prompt(frm);
    toggle_tone(frm);
  },

  letter_type(frm){
     toggle_prompt(frm);
     toggle_tone(frm);
 }
});

function toggle_prompt(frm) {
  const hiddenTypes = ["معرفی", "بارگیری", "گواهی اشتغال به کار"];
  frm.toggle_display("prompt", !hiddenTypes.includes(frm.doc.letter_type));
}

function toggle_tone(frm){
  const hiddenTypes = ["معرفی", "بارگیری", "گواهی اشتغال به کار"];
  frm.toggle_display("tone_of_writing", !hiddenTypes.includes(frm.doc.letter_type));
}

function bargiri_dialog(resolve, state){
  return new frappe.ui.Dialog({
    title: __("جزئیات تکمیلی (ذخیره نمی‌شود)"),
    fields:[
        {fieldtype: "Data", fieldname: "contract_party", label: __("طرف قرارداد"), reqd: 1 },
        {fieldtype: "Data", fieldname: "authority", label: __("مرجع"), reqd: 1},
        {fieldtype: "Data", fieldname: "waste_type", label: __("نوع پسماند"), reqd: 1},
        {fieldtype: "Data", fieldname: "period", label: __("دوره زمانی"), reqd: 1},
        {fieldtype: "Date", fieldname: "start_date", label: __("زمان شروع"), reqd: 0},
        {fieldtype: "Date", fieldname: "end_date", label:__("زمان پایان"), reqd:0}
     ],
     primary_action_label: __("تأیید"),
     primary_action(values) {
      values = values || this.get_values();
      if (!values) return; // validation failed; dialog shows errors
      state.confirmed = true;
      this.hide();
      resolve(values);
     }
   });
}

function govahi_dialog(resolve, state) {
  return new frappe.ui.Dialog({
    title: __("جزئیات تکمیلی (ذخیره نمی‌شود)"),
    fields: [
      { fieldtype: "Data", fieldname: "gender",          label: __("جنسیت"), reqd: 1 },
      { fieldtype: "Data", fieldname: "name",        label: __("اسم فرد مورد نظر"), reqd: 1 },
      { fieldtype: "Data", fieldname: "father_name",   label: __("نام پدر"), reqd: 1 },
      { fieldtype: "Data", fieldname: "national_code", label: __("شماره ملی"), reqd: 1 },
      { fieldtype: "Data", fieldname: "study_level", label: __("مدرک"), reqd:1},
      { fieldtype: "Data", fieldname: "major",         label: __("رشته"), reqd: 1 },
      { fieldtype: "Data", fieldname: "specialize",    label: __("گرایش"), reqd: 1 }, // fixed "label"
      { fieldtype: "Data", fieldname: "uni",           label: __("دانشگاه"), reqd: 1 },
      { fieldtype: "Date", fieldname: "from_date1",    label: __("از تاریخ 1"), reqd: 1 },
      { fieldtype: "Date", fieldname: "to_date1",      label: __("تا تاریخ 1"), reqd: 0 },
      // Decide which one you really want:
      { fieldtype: "Date", fieldname: "from_date2",    label: __("از تاریخ 2"), reqd: 0 }, // or rename to to_date2
      { fieldtype: "Data", fieldname: "company",       label: __("شرکت"), reqd: 1 },
      { fieldtype: "Data", fieldname: "post",          label: __("سمت"), reqd: 1 },
      { fieldtype: "Data", fieldname: "to",            label: __("مرجع"), reqd: 1 },
    ],
    primary_action_label: __("تأیید"),
    primary_action(values) {
      values = values || this.get_values();
      if (!values) return; // validation failed; dialog shows errors
      state.confirmed = true;
      this.hide();
      resolve(values);
    }
  });
}


function moarefi_dialog(resolve, state){
  return new frappe.ui.Dialog({
      title: __("جزئیات تکمیلی (ذخیره نمی‌شود)"),
      fields: [
        { fieldtype: "Data", fieldname: "name", label: __("اسم فرد مورد نظر"), reqd: 1 },
        { fieldtype: "Data", fieldname: "gender", label: __("جنسیت"), reqd: 1},
        { fieldtype: "Data", fieldname: "national_code",     label: __("شماره ملی"), reqd: 1 },
        { fieldtype: "Data", fieldname: "duty",    label: __("امور مورد نظر"), reqd: 1 }
      ],
      primary_action_label: __("تأیید"),
      primary_action(values) {
        values = values || this.get_values();
        if (!values) return; // validation failed; dialog shows errors
        state.confirmed = true;
        this.hide();
        resolve(values);     // e.g. {temp_subject, temp_nid, temp_note, temp_task}
      }
    });
}

/** -------- Dialog for UI-only inputs (only when letter_type === "test") -------- */
function collect_runtime_values_if_needed(frm) {
  if (!["بارگیری","معرفی", "گواهی اشتغال به کار"].includes(frm.doc.letter_type)) {
    return Promise.resolve({}); // no extra inputs needed
  }

  return new Promise((resolve) => {
    const state = { confirmed: false };
    let d;
    if (frm.doc.letter_type === "معرفی"){
       d = moarefi_dialog(resolve, state);
    }else if (frm.doc.letter_type === "گواهی اشتغال به کار"){
       d = govahi_dialog(resolve, state);
    }else if (frm.doc.letter_type === "بارگیری"){
       d = bargiri_dialog(resolve, state);
    }
    if (!d) {
      resolve(null);
      return;
    }
    // Cancel (X/ESC/click-outside) → resolve(null) so caller can abort cleanly
    d.onhide = () => { if (!state.confirmed) resolve(null); };

    d.show();
  });
}

/** ---------------- Buttons ---------------- **/
function addGenerateLetterButton(frm) {
  frm.add_custom_button(__('Generate Letter'), async () => {
    if (frm.is_dirty()) {
      frappe.msgprint(__('Please save first.'));
      return;
    }

    const runtime_values = await collect_runtime_values_if_needed(frm);
    if (runtime_values === null) {
      // user cancelled → stop; keep button usable
      frappe.show_alert({ message: __('لغو شد'), indicator: 'orange' });
      return;
    }

    frappe.msgprint({
         title: __("ورودی‌ها"),
         indicator: "blue",
         message: `<pre>${JSON.stringify(runtime_values, null, 2)}</pre>`
     });


    try {
     let method = "";
     if (frm.doc.letter_type === "معرفی"){
        method = 'letter_ai.api.letter_ai.generate_moarefi_letter';
     }else if (frm.doc.letter_type === "گواهی اشتغال به کار"){
        method = 'letter_ai.api.letter_ai.generate_govahi_letter';
     }else if (frm.doc.letter_type === "بارگیری"){
        method = 'letter_ai.api.letter_ai.generate_bargiri_letter'; 
     }
      await frappe.call({
        method: method,
        args: { docname: frm.doc.name, runtime_values:runtime_values },
        freeze: true,
        freeze_message: __('در حال تولید نامه… لطفاً صبر کنید.')
      });

      await frm.reload_doc();
      frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
      frappe.show_alert({ message: __('نامه تولید شد'), indicator: 'green' });
    } catch (e) {
      frappe.msgprint(__('Error: {0}', [e.message || e]));
    }
  });
}

function addRegenerateButton(frm) {
  frm.add_custom_button(__('Regenerate with Edits'), async () => {
    if (frm.is_dirty()) {
      frappe.msgprint(__('Please save first.'));
      return;
    }

    const runtime_values = await collect_runtime_values_if_needed(frm);
    if (runtime_values === null) {
      frappe.show_alert({ message: __('لغو شد'), indicator: 'orange' });
      return;
    }

    try {
      await frappe.call({
        method: 'letter_ai.api.letter_ai.edit_letter',
        args: {
          docname: frm.doc.name,
          type: frm.doc.letter_type,
          tone: frm.doc.tone_of_writing,
          rec: frm.doc.recipient_company,
          runtime_values
        },
        freeze: true,
        freeze_message: __('در حال بازتولید نامه… لطفاً صبر کنید.')
      });

      await frm.reload_doc();
      frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
      frappe.show_alert({ message: __('نامه به‌روزرسانی شد'), indicator: 'green' });
    } catch (e) {
      frappe.msgprint(__('Error: {0}', [e.message || e]));
    }
  });
}

