import frappe
import json
import requests

@frappe.whitelist(allow_guest=True)
def event_webhook(
    is_rack,
    rack_id: str=None,
    rack_cmd: str=None,
    firmware: str=None,
    rack_time: str=None,
    rack_status: dict=None,
    channels=None,
    pump_id: str=None,
    pump_type: str=None,
    start_second: str=None,
    end_second: str=None,
    pump_op_status: str=None,
    set_flow_rate: str=None,
    increment_rate: str=None,
    pump_alarm_status: str=None,
):
    if is_rack:
        rack_op_status = rack_status.get("operation_status")
        power_type = rack_status.get("power_type")
        battery_status = rack_status.get("battery_status")

        rack = update_rack(
            rack_id,
            firmware,
            rack_op_status,
            power_type,
            battery_status,
        )

        for ch in channels:
            channel_id = ch.get("channel")
            pump_id = ch.get("device_id")
            normstatus = ch.get("normstatus")

            if not normstatus or pump_id in ["X", "?"]:
                continue
                # frappe.throw("Empty channel")

            start_second = normstatus.get("start_second")
            end_second = normstatus.get("end_second")
            pump_op_status = normstatus.get("operation_status")
            set_flow_rate = float(normstatus.get("set_flow_rate"))
            increment_rate = float(normstatus.get("increment_rate"))
            pump_alarm_status = normstatus.get("alarm_status")

            pump = update_pump(
                pump_id,
                pump_type,
                pump_op_status,
                set_flow_rate,
                increment_rate,
                pump_alarm_status,
                rack.name,
            )

            notify_client(
                device_id=pump_id,
                operation_status=pump_op_status,
                flow_rate=set_flow_rate,
                increment_rate=increment_rate,
                alarm_status=pump_alarm_status,
                channel=channel_id,
                patient_id=pump.patient_id,
            )

            create_pump_read(
                pump_id=pump.name,
                start_second=start_second,
                end_second=end_second,
                operation_status=pump_op_status,
                set_flow_rate=set_flow_rate,
                increment_in_value_delivered=increment_rate,
                alarm=pump_alarm_status,
            )
            if pump.patient_id:
                ## Send to HIS
                pass

    else:
        pump = update_pump(
            pump_id,
            pump_type,
            pump_op_status,
            set_flow_rate,
            increment_rate,
            pump_alarm_status,
        )

        notify_client(
            device_id=pump_id,
            operation_status=pump_op_status,
            flow_rate=set_flow_rate,
            increment_rate=increment_rate,
            alarm_status=pump_alarm_status,
            patient_id=pump.patient_id,
        )

        create_pump_read(
            pump_id=pump.name,
            start_second=start_second,
            end_second=end_second,
            operation_status=pump_op_status,
            set_flow_rate=set_flow_rate,
            increment_in_value_delivered=increment_rate,
            alarm=pump_alarm_status,
        )
        if pump.patient_id:
            ## Send to HIS
            pass

    frappe.db.commit()


def update_rack(
    device_id,
    software_version,
    operation_status,
    power_type,
    battery_status,
):
    racks = frappe.get_all("Rack", {"name": device_id})
    if racks:
        rack = frappe.get_doc("Rack", device_id)
    
    else:
        rack = frappe.new_doc("Rack")
        rack.device_id = device_id
        rack.device_name = device_id

    rack.software_version = software_version
    rack.operation_status = operation_status
    rack.power_type = power_type
    rack.battery_status = battery_status
    rack.save(ignore_permissions=True)

    return rack



def update_pump(
    device_id,
    pump_type,
    operation_status,
    set_flow_rate,
    increment_rate,
    alarm_status,
    rack_id=None
):
    pumps = frappe.get_all("Pump", {"name": device_id})
    if pumps:
        pump = frappe.get_doc("Pump", device_id)
    
    else:
        pump = frappe.new_doc("Pump")
        pump.device_id = device_id
        pump.device_name = device_id

    pump.pump_type = pump_type
    pump.operation_status = operation_status
    pump.set_flow_rate = set_flow_rate
    pump.increment_in_value_delivered = increment_rate
    pump.alarm_status = alarm_status
    if rack_id:
        pump.rack = rack_id
    pump.save(ignore_permissions=True)

    return pump


def create_pump_read(
    pump_id,
    start_second,
    end_second,
    operation_status,
    set_flow_rate,
    increment_in_value_delivered,
    alarm,
):
    read = frappe.new_doc("Pump Read")
    read.pump_id = pump_id
    read.start_second = start_second
    read.end_second = end_second
    read.set_flow_rate = set_flow_rate
    read.increment_in_value_delivered = increment_in_value_delivered
    read.operation_status = operation_status
    read.alarm = alarm
    read.insert(ignore_permissions=True)


def notify_client(
    device_id,
    operation_status,
    flow_rate,
    increment_rate,
    alarm_status,
    vtbi=None,
    channel=None,
    patient_id=None,
):
    alarm_status = frappe.get_value(
        "Pump Alarm Status",
        alarm_status,
        "description",
    )
    frappe.publish_realtime(
        f"update_state_{device_id}",
        message={
            "device_id": device_id,
            "operation_status": operation_status,
            "flow_rate": flow_rate,
            "increment_rate": increment_rate,
            "alarm_status": alarm_status,
            "vtbi": vtbi,
            "channel": channel,
            "patient_id": patient_id,
        }
    )


@frappe.whitelist()
def get_pump_devices(patient_room=None):
    if patient_room:
        pumps = frappe.get_list(
            "Pump",
            filters={"patient_room": patient_room},
            fields=["*"]
        )

        for pump in pumps:
            if pump.rack:
                pump.is_rack = True
                
                
        
    
    return frappe.get_list("Pump", fields=["*"])