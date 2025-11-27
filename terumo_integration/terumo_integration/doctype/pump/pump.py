# Copyright (c) 2025, WOW Digital Information Technology and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Pump(Document):
	pass


@frappe.whitelist()
def assign_patient(pump_id, patient_id):
	try:
		pump = frappe.get_doc("Pump", pump_id)
		pump.patient_id = patient_id
		pump.save(ignore_permissions=True)

		return {"success": True}
	
	except:
		return {"success": False}
	

@frappe.whitelist()
def unassign_patient(pump_id):
	try:
		pump = frappe.get_doc("Pump", pump_id)
		pump.patient_id = ""
		pump.save(ignore_permissions=True)

		return {"success": True}
	
	except:
		return {"success": False}