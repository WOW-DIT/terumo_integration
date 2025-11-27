// Copyright (c) 2025, WOW Digital Information Technology and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pump', {
	refresh: function(frm) {
		if(!frm.doc.name.startsWith("new")) {
			if(!frm.doc.patient_id) {
				frm.add_custom_button("Assign Patient", () => {
					assign_patient(frm);
				}).addClass("btn-primary");
			} else {
				frm.add_custom_button("Un-Assign Patient", () => {
					unassign_patient(frm);
				}).addClass("btn-primary");
			}
		}
	}
});


function assign_patient(frm) {
	const d = new frappe.ui.Dialog({
        title: __('Assign Patient'),
        fields: [
            {
                fieldname: 'patient',
                label: __('Patient'),
                fieldtype: 'Link',
				options: 'Patients',
                reqd: 1,
                description: __('Select a patient')
            }
        ],
        primary_action_label: __('Assign'),
        primary_action(values) {
            let patient_id = values.patient;

            d.get_primary_btn().prop('disabled', true);

            frappe.call({
                method: 'terumo_integration.terumo_integration.doctype.pump.pump.assign_patient',
                args: {
                    pump_id: frm.doc.name,
                    patient_id: patient_id,
                },
                freeze: true,
                freeze_message: __('Assigning patient...'),
                callback(res) {
					console.log(res.message)
                    d.hide();
                    if (res.message && res.message.success) {
                        frappe.msgprint(res.message?.message || __('Patient assigned successfully.'));
                        reload_page();
                    } else {
                        frappe.msgprint(res.message?.message || __('Patient assignment failed.'));
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}

function unassign_patient(frm) {
	const d = new frappe.ui.Dialog({
        title: __('Assign Patient'),
        fields: [],
        primary_action_label: __('Un-Assign'),
        primary_action(values) {

            d.get_primary_btn().prop('disabled', true);

            frappe.call({
                method: 'terumo_integration.terumo_integration.doctype.pump.pump.unassign_patient',
                args: {
                    pump_id: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Un-Assigning patient...'),
                callback(res) {
					console.log(res.message)
                    d.hide();
                    if (res.message && res.message.success) {
                        frappe.msgprint(res.message?.message || __('Patient unassigned successfully.'));
                        reload_page();
                    } else {
                        frappe.msgprint(res.message?.message || __('Patient unassignment failed.'));
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}

function reload_page(){
    setTimeout(() => {
        location.reload();
    }, 2000);
}