const hiddenTypes = ["گزارش", "معرفی", "بارگیری", "گواهی اشتغال به کار"];
const TYPE_TO_KEY = {
  "معرفی": "moarefi",
  "گواهی اشتغال به کار": "govahi",
  "بارگیری": "bargiri",
  "گزارش": "gozaresh",
};

frappe.ui.form.on("letter_ai", {
   onload_post_render(frm){
     frm.toggle_display("ref_date", false);
   },
   refresh(frm) {
    // show/hide preview
    frm.toggle_display("generated_letter", !!frm.doc.generated_letter);

    // buttons
    addGenerateLetterButton(frm);
    if (frm.doc.generated_letter) addRegenerateButton(frm);

    // toggle fields based on type
    toggle_field(frm, "prompt");
    toggle_field(frm, "tone_of_writing");
    toggle_field(frm, "ref_letter");
    toggle_field(frm, "ref_date_djalali");
    toggle_field(frm, "attachments");
  },

  letter_type(frm) {
    toggle_field(frm, "prompt");
    toggle_field(frm, "tone_of_writing");
    toggle_field(frm, "ref_letter");
    toggle_field(frm, "ref_date_djalali");
    toggle_field(frm, "attachments");
  }
});

function toggle_field(frm, field_name){
  frm.toggle_display(field_name, !hiddenTypes.includes(frm.doc.letter_type));
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
      if (!values) return;
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
      { fieldtype: "Data", fieldname: "gender", label: __("جنسیت"), reqd: 1 },
      { fieldtype: "Data", fieldname: "name", label: __("اسم فرد مورد نظر"), reqd: 1 },
      { fieldtype: "Data", fieldname: "father_name", label: __("نام پدر"), reqd: 1 },
      { fieldtype: "Data", fieldname: "national_code", label: __("شماره ملی"), reqd: 1 },
      { fieldtype: "Data", fieldname: "study_level", label: __("مدرک"), reqd:1},
      { fieldtype: "Data", fieldname: "major", label: __("رشته"), reqd: 1 },
      { fieldtype: "Data", fieldname: "specialize", label: __("گرایش"), reqd: 1 },
      { fieldtype: "Data", fieldname: "uni", label: __("دانشگاه"), reqd: 1 },
      { fieldtype: "Date", fieldname: "from_date1", label: __("از تاریخ 1"), reqd: 1 },
      { fieldtype: "Date", fieldname: "to_date1", label: __("تا تاریخ 1"), reqd: 0 },
      { fieldtype: "Date", fieldname: "from_date2", label: __("از تاریخ 2"), reqd: 0 },
      { fieldtype: "Data", fieldname: "company", label: __("شرکت"), reqd: 1 },
      { fieldtype: "Data", fieldname: "post", label: __("سمت"), reqd: 1 },
      { fieldtype: "Data", fieldname: "to", label: __("مرجع"), reqd: 1 }
    ],
    primary_action_label: __("تأیید"),
    primary_action(values) {
      values = values || this.get_values();
      if (!values) return;
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
      { fieldtype: "Data", fieldname: "national_code", label: __("شماره ملی"), reqd: 1 },
      { fieldtype: "Data", fieldname: "duty", label: __("امور مورد نظر"), reqd: 1 }
    ],
    primary_action_label: __("تأیید"),
    primary_action(values) {
      values = values || this.get_values();
      if (!values) return;
      state.confirmed = true;
      this.hide();
      resolve(values);
    }
  });
}

function gozaresh_dialog(resolve, state){
  return new frappe.ui.Dialog({
    title: __("جزئیات تکمیلی (ذخیره نمی‌شود)"),
    fields: [
      { fieldtype: "Data", fieldname: "report_name", label: __("نام کامل گزارش"), reqd: 1 },
      { fieldtype: "Date", fieldname: "report_date", label: __("تاریخ گزارش"), reqd: 1}
    ],
    primary_action_label: __("تأیید"),
    primary_action(values) {
      values = values || this.get_values();
      if (!values) return;
      state.confirmed = true;
      this.hide();
      resolve(values);
    }
  });
}

/** -------- Dialog for UI-only inputs -------- */
function collect_runtime_values_if_needed(frm) {
  // Only template-backed types need UI-only runtime inputs
  const key = TYPE_TO_KEY[frm.doc.letter_type];
  if (!key) return Promise.resolve({});

  return new Promise((resolve) => {
    const state = { confirmed: false };
    let d;

    switch (key) {
      case "moarefi":  d = moarefi_dialog(resolve, state); break;
      case "govahi":   d = govahi_dialog(resolve, state); break;
      case "bargiri":  d = bargiri_dialog(resolve, state); break;
      case "gozaresh": d = gozaresh_dialog(resolve, state); break;
      default: resolve(null); return;
    }

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
      frappe.show_alert({ message: __('لغو شد'), indicator: 'orange' });
      return;
    }

    try {
      const key = TYPE_TO_KEY[frm.doc.letter_type];
      const method = key
        ? 'letter_ai.api.letter_ai.generate_from_template'
        : 'letter_ai.api.letter_ai.generate_letter';

      const args = key
        ? { docname: frm.doc.name, template_key: key, runtime_values }
        : { docname: frm.doc.name };

      const r = await frappe.call({
        method,
        args,
        freeze: true,
        freeze_message: __('در حال تولید نامه… لطفاً صبر کنید.')
      });

      if (r && r.message) frm.doc.generated_letter = r.message;

      await frm.reload_doc();
      frm.toggle_display('generated_letter', !!frm.doc.generated_letter);
      frappe.show_alert({ message: __('نامه تولید شد'), indicator: 'green' });
    } catch (e) {
      frappe.msgprint(__('Error: {0}', [e.message || e]));
      // optional console.error(e);
    }
  });
}


function addRegenerateButton(frm) {
  frm.add_custom_button(__('Regenerate with Edits'), async () => {
    if (frm.is_dirty()) {
      frappe.msgprint(__('Please save first.'));
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
          ref_let: frm.doc.ref_letter,
          ref_date: frm.doc.ref_date,
          attach: frm.doc.attachments
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



