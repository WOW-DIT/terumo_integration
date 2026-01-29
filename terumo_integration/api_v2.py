import frappe
import json
import requests

@frappe.whitelist(allow_guest=True)
def event_webhook(
    is_rack,
    rack_id: str=None,
    rack_status: dict={},
    firmware: str=None,
    start_second: str=None,
    end_second: str=None,
    channels=None,
    pump_id: str=None,
    pump_type: str="Infusion Pump",
    pump_op_status: str=None,
    pump_alarm_status: list=[],
    ac_power_detector: bool=None,
    pump_power_status: dict={},
    pump_operation_monitor: dict=None,
    syringe_status: int=0,
    set_flow_rate: float=0.0,
    volume_delivered: float=0.0,
    vtbi: dict=None,
    dosage: dict=None,
    weight: float=None,
    dilution: dict=None,
    drug_library: dict=None,
    occlusion_pressure_settings: dict=None,
    increment_rate: str=None,
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
                device_id=pump_id,
                pump_type=None,
                operation_status=pump_op_status,
                set_flow_rate=set_flow_rate,
                increment_rate=increment_rate,
                alarm_status=pump_alarm_status,
                syringe_status=syringe_status,
                volume_delivered=volume_delivered,
                pump_power_status=pump_power_status,
                rack_id=rack.name,
            )

            return notify_client(
                device_name=pump.device_name,
                device_id=pump_id,
                operation_status=pump_op_status,
                flow_rate=set_flow_rate,
                increment_rate=increment_rate,
                alarm_status=pump_alarm_status,
                channel=channel_id,
                patient_id=pump.patient_id,
                is_rack=is_rack,
                rack_id=rack.name,
                rack_name=rack.device_name,
                rack_status=rack_status,
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
        
        ## Update rack status
        return notify_client(
            device_name=pump.device_name,
            device_id=pump_id,
            operation_status=pump_op_status,
            flow_rate=set_flow_rate,
            increment_rate=increment_rate,
            alarm_status=pump_alarm_status,
            channel=channel_id,
            patient_id=pump.patient_id,
            is_rack=is_rack,
            rack_id=rack.name,
            rack_name=rack.device_name,
            rack_status=rack_status,
        )
    
    pump_op_status = map_pump_op_status(pump_op_status)

    pump = update_pump(
        device_id=pump_id,
        pump_type=pump_type,
        operation_status=pump_op_status,
        set_flow_rate=set_flow_rate,
        increment_rate=increment_rate,
        alarm_status=None,
        syringe_status=syringe_status,
        volume_delivered=volume_delivered,
        pump_power_status=pump_power_status,
    )

    if not pump.alarms_template:
        active_alarms = []
    else:
        active_alarms = update_alarm_statuses(pump.alarms_template, pump_alarm_status)

    return notify_client(
        device_name=pump.device_name,
        device_id=pump_id,
        operation_status=pump_op_status,
        flow_rate=set_flow_rate,
        increment_rate=increment_rate,
        alarm_status=None,
        vtbi=vtbi,
        active_alarms=active_alarms,
        pump_power_status=pump_power_status,
        patient_id=pump.patient_id,
        is_rack=is_rack,
        rack_id=pump.rack,
    )

    create_pump_read(
        pump_id=pump.name,
        start_second=start_second,
        end_second=end_second,
        operation_status=pump_op_status,
        set_flow_rate=set_flow_rate,
        increment_in_value_delivered=increment_rate,
        # alarm=pump_alarm_status,
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
    alarm_status: str=None,
    syringe_status: int=0,
    volume_delivered: float=0.0,
    pump_power_status: dict={},
    rack_id=None,
):
    pumps = frappe.get_all("Pump", {"name": device_id})
    if pumps:
        pump = frappe.get_doc("Pump", device_id)
    
    else:
        pump = frappe.new_doc("Pump")
        pump.device_id = device_id
        pump.device_name = device_id

    pump.syringe_status = syringe_status
    pump.operation_status = operation_status
    pump.set_flow_rate = set_flow_rate
    pump.volume_delivered = volume_delivered
    pump.increment_in_value_delivered = increment_rate
    pump.alarm_status = alarm_status
    
    if pump_type:
        pump.pump_type = pump_type
        pump.alarms_template = pump_type

    ## Power Status
    pump.battery_level = pump_power_status.get("battery_level")
    pump.power_type = pump_power_status.get("power_type")
    pump.sub_battery_status = "Normal" if pump_power_status.get("sub_battery") == 1 else "Abnormal"
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
    # alarm,
):
    read = frappe.new_doc("Pump Read")
    read.pump_id = pump_id
    read.start_second = start_second
    read.end_second = end_second
    read.set_flow_rate = set_flow_rate
    read.increment_in_value_delivered = increment_in_value_delivered
    read.operation_status = operation_status
    # read.alarm = alarm
    read.insert(ignore_permissions=True)


def notify_client(
    device_name,
    device_id,
    operation_status,
    flow_rate,
    increment_rate,
    alarm_status,
    active_alarms=[],
    pump_power_status={},
    vtbi=None,
    channel=None,
    patient_id=None,
    is_rack=False,
    rack_id=None,
    rack_name=None,
    rack_status={}
):
    alarm_description = frappe.get_value(
        "Pump Alarm Status",
        alarm_status,
        "description",
    )
    realtime_message = {
        "device_name": device_name,
        "device_id": device_id,
        "operation_status": operation_status,
        "set_flow_rate": flow_rate,
        "increment_rate": increment_rate,
        "alarm_status": alarm_status,
        "alarm_description": alarm_description,
        "active_alarms": active_alarms,
        "power_type": pump_power_status.get("power_type"),
        "battery_level": pump_power_status.get("battery_level"),
        "vtbi": vtbi,
        "channel": channel,
        "patient_id": patient_id,
        "is_rack": is_rack,
        "rack_id": rack_id,
        "rack_name": rack_name,
        "rack_status": rack_status,
    }
    frappe.publish_realtime(
        f"update_state_{device_id}",
        message=realtime_message,
    )

    return realtime_message


@frappe.whitelist()
def get_pump_devices(patient_room=None):
    if patient_room:
        pumps = frappe.get_list(
            "Pump",
            filters={"patient_room": patient_room},
            fields=["*"]
        )
    else:
        pumps = frappe.get_list("Pump", fields=["*"])

    for pump in pumps:
        if pump.rack:
            pump.is_rack = True
            
            rack = frappe.get_doc("Rack", pump.rack)
            pump.rack_id = pump.rack
            pump.rack_name = rack.device_name
            pump.rack_status = {
                "operation_status": rack.operation_status_description,
                "power_type": rack.power_type,
                "battery_status": rack.battery_status,
            }

        if not pump.rack:
            pump.is_rack = False

            if not pump.alarms_template:
                pump.active_alarms = []
            else:
                pump.active_alarms = get_alarm_statuses(pump.alarms_template)

    return pumps
    


def map_pump_op_status(pump_op_status):
    status = frappe.db.sql("""
        SELECT s.name
        FROM `tabPump Operation Status` AS s
        WHERE s.code=%s OR s.standalone_mapping_value=%s
        """,
        (pump_op_status, pump_op_status,),
        as_dict=True
    )

    if status and status[0].name:
        return status[0].name
    
    return None


def get_alarm_statuses(template_name: str) -> list:
    template = frappe.get_doc("Pump Alarms Template", template_name)

    active_alarms = []
    for alarm in template.alarms:
        if alarm.active:
            active_alarms.append(alarm.description)

    return active_alarms


def update_alarm_statuses(template_name: str, pump_alarm_statuses: list) -> list:
    template = frappe.get_doc("Pump Alarms Template", template_name)
    
    active_alarms = []
    
    rows_by_bit = {row.bit_number: row for row in template.alarms}

    for row in template.alarms:
        row.active = 0

    for bit_number, bit_value in enumerate(pump_alarm_statuses):
        ## Get child table row by bit_number, or index from alarms list.
        row = rows_by_bit.get(bit_number)
        if not row:
            continue
        
        if bit_value == 1:
            row.active = 1
            active_alarms.append(row.description)
        else:
            row.active = 0  # للتوضيح، مع إنه صفّرناها فوق

    template.save(ignore_permissions=True)

    return active_alarms