"""Read-only LI-COR grammar adapter, based on EC-Monitor (MIT).

Source: davidulicio/EC-Monitor at 797a96c; see docs/EC_MONITOR_LICENSE.txt.
No SSH, web login, arbitrary query console or instrument write operation exists.
"""
import math
import re
import socket
import time
from datetime import datetime, timedelta, timezone

# Exact allowlist is deliberately stricter than EC-Monitor's generic query guard.
QUERIES = ("(EmbeddedSW ?)", "(Coef ?)", "(Outputs ?)", "(Calibrate ?)", "(Data ?)", "(Diagnostics ?)", "(Info ?)", "(Fluxes(Status ?))", "(CH4 ?)", "(FlowBox ?)", "(Clock ?)")
ORDER_7200 = "Ndx DiagVal DiagVal2 DiagBits AGC AvgSS CO2SS H2OSS DeltaSS CO2Raw CO2D CO2MG H2ORaw H2OD H2OG Temp Pres Aux Aux2 Aux3 Aux4 Cooler ChopperCooler SFVin Time Date CO2MF CO2MFd H2OMF H2OMFd DewPt APres DPres AvgTemp TempIn TempOut H2OAW H2OAWO CO2AW CO2AWO MeasFlowRate VolFlowRate FlowPressure FlowPower FlowDrive SECONDS NANOSECONDS CH4 CH4D RSSI DIAG U V W TS SOS AnemDiag DSIVin".split()
ORDER_7500 = "Ndx DiagVal CO2Raw CO2D H2ORaw H2OD Temp Pres Aux Aux2 Aux3 Aux4 Cooler Time Date CO2MF CO2MFd H2OMF H2OMFd DewPt DPres TempIn TempOut".split()
# For labelled data the transmitted case is preserved (Temp and TEMP differ).
METRICS = {
    "CO2MF": ("CO₂ mole fraction", "µmol/mol", "Gas"),
    "CO2MFd": ("CO₂ dry mole fraction", "µmol/mol", "Gas"),
    "CO2D": ("CO₂ density", "mmol/m³", "Gas"),
    "H2OMF": ("H₂O mole fraction", "mmol/mol", "Gas"),
    "H2OD": ("H₂O density", "mmol/m³", "Gas"),
    "Temp": ("Block temperature", "°C", "Cell"),
    "AvgTemp": ("Cell temperature", "°C", "Cell"),
    "TempIn": ("Inlet temperature", "°C", "Cell"),
    "TempOut": ("Outlet temperature", "°C", "Cell"),
    "Pres": ("Cell pressure", "kPa", "Cell"),
    "DPres": ("Differential pressure", "kPa", "Cell"),
    "Cooler": ("Detector cooler", "V", "Cell"),
    "AvgSS": ("Signal strength", "%", "Signal"),
    "CO2SS": ("CO₂ signal strength", "%", "Signal"),
    "H2OSS": ("H₂O signal strength", "%", "Signal"),
    "DeltaSS": ("Delta signal strength", "", "Signal"),
    "MeasFlowRate": ("Flow rate", "SLPM", "Flow"),
    "FlowDrive": ("Pump drive", "%", "Flow"),
    "FlowPressure": ("Flow pressure", "kPa", "Flow"),
    "SetFlowRate": ("Flow setpoint", "SLPM", "Flow"),
    "CH4": ("CH₄ mole fraction", "µmol/mol", "Methane"),
    "RSSI": ("LI-7700 signal strength", "%", "Methane"),
    "DropRate": ("LI-7700 drop rate", "%", "Methane"),
    "TEMP": ("LI-7700 temperature", "°C", "Methane"),
    "U": ("Wind u", "m/s", "Wind"), "V": ("Wind v", "m/s", "Wind"),
    "W": ("Wind w", "m/s", "Wind"), "TS": ("Sonic temperature", "°C", "Wind"),
    "WindSpeed": ("Horizontal wind speed", "m/s", "Wind"),
    "AnemDiag": ("Sonic diagnostic", "", "Wind"),
    "Vin": ("SmartFlux supply", "V", "System"),
    "NumSat": ("GPS satellites", "", "System"),
}


def split_records(buffer):
    """Return balanced records and a trailing partial record, including quotes."""
    depth, quote, start, consumed = 0, False, None, 0
    records = []
    for index, char in enumerate(buffer):
        if char == '"':
            quote = not quote
        elif not quote:
            if char == "(":
                if depth == 0:
                    start = index
                depth += 1
            elif char == ")" and depth:
                depth -= 1
                if depth == 0:
                    records.append(buffer[start:index + 1])
                    consumed = index + 1
    return records, buffer[consumed:]


def parse(record):
    """Strict parenthesised tree with a depth/size limit."""
    if len(record) > 262144:
        raise ValueError("Record too large")
    def node(pos, depth=0):
        if depth > 32 or pos >= len(record) or record[pos] != "(":
            raise ValueError("Malformed record")
        pos += 1
        match = re.match(r"[^\s()]+", record[pos:])
        if not match:
            raise ValueError("Missing tag")
        name = match.group()
        pos += len(name)
        while pos < len(record) and record[pos].isspace():
            pos += 1
        if pos < len(record) and record[pos] == "(":
            children = []
            while pos < len(record):
                if record[pos].isspace():
                    pos += 1
                elif record[pos] == "(":
                    child, pos = node(pos, depth + 1)
                    children.append(child)
                elif record[pos] == ")":
                    return (name, children), pos + 1
                else:
                    raise ValueError("Unexpected container value")
        else:
            begin, quoted = pos, False
            while pos < len(record):
                if record[pos] == '"':
                    quoted = not quoted
                if record[pos] == ")" and not quoted:
                    return (name, record[begin:pos].strip().strip('"')), pos + 1
                pos += 1
        raise ValueError("Incomplete record")
    result, end = node(0)
    if record[end:].strip():
        raise ValueError("More than one record")
    return result


def flatten(node, prefix=""):
    name, value = node
    key = prefix + name
    if isinstance(value, str):
        return {key: value}
    result = {}
    for child in value:
        result.update(flatten(child, key + "/"))
    return result


def read_only_query(command):
    if command not in QUERIES:
        raise ValueError("Instrument writes and arbitrary queries are disabled.")
    leaves = flatten(parse(command)).values()
    if not all(value in {"", "?"} for value in leaves) or "?" not in leaves:
        raise ValueError("Instrument writes are disabled.")
    return (command + "\n").encode("ascii")


def number(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (ValueError, TypeError):
        return None


def decode(records, numeric_lines=(), utc_offset=-5):
    values = {}
    for text in records:
        try:
            values.update(flatten(parse(text)))
        except ValueError:
            continue
    inferred = False
    if not any(k.startswith("Data/") for k in values) and numeric_lines:
        order=ORDER_7500 if "7500" in values.get("EmbeddedSW/Model", "") else ORDER_7200
        enabled = [tag for tag in order if values.get("Outputs/ENet/"+tag, "").upper() in {"TRUE", "1"}]
        if enabled:
            for line in reversed(numeric_lines):
                parts = line.split()
                if len(parts) == len(enabled) and all(number(x) is not None for x in parts):
                    values.update({"Data/"+k:v for k,v in zip(enabled,parts)})
                    inferred=True
                    break
    allowed_roots = {"Data", "CH4Data", "SonicData", "FlowBox"}
    measured = {}
    for path, value in values.items():
        root, tag = path.split("/", 1)[0], path.split("/")[-1]
        if (root in allowed_roots or path in {"Fluxes/Status/SmartFlux/Vin", "Fluxes/Status/SmartFlux/GPS/NumSat"}) and tag in METRICS and number(value) is not None:
            measured[tag] = number(value)
    diag_value = number(values.get("Data/DiagVal"))
    model = values.get("EmbeddedSW/Model", "")
    enclosed = "7200" in model or (diag_value is not None and diag_value > 255)
    if "AvgSS" not in measured:
        signal = number(values.get("Diagnostics/Path"))
        if signal is None and diag_value is not None:
            signal = (int(diag_value) & 15) * 6.67
        if signal is not None:
            measured["AvgSS"] = round(signal, 2)
    if all(tag in measured for tag in ["U", "V"]):
        measured["WindSpeed"] = round(math.hypot(measured["U"], measured["V"]), 3)
    flags=[]
    mapping=[("Sync",["SYNCH","SYNC"],4,"fault"),("PLL",["PLL"],5,"fault"),("Detector",["DetOK"],6,"fault"),("Chopper",["Chopper"],7,"fault")]
    if enclosed:
        mapping += [("Differential pressure",["PDif"],8,"warning"),("Internal references",["AuxIn"],9,"fault"),("Inlet thermocouple",["Tin"],10,"warning"),("Outlet thermocouple",["Tout"],11,"warning"),("Head detection",["Head"],12,"fault")]
    for label,tags,bit,severity in mapping:
        reported = next((values["Diagnostics/"+t] for t in tags if "Diagnostics/"+t in values), None)
        ok = str(reported).upper() in {"TRUE","1","YES","OK"} if reported is not None else bool(int(diag_value) & (1 << bit)) if diag_value is not None else None
        flags.append({"label":label,"ok":ok,"severity":severity})
    issues=[]
    def issue(level,title,detail):
        issues.append({"severity":level,"title":title,"detail":detail})
    for flag in flags:
        if flag["ok"] is False:
            issue(flag["severity"],flag["label"]+" diagnostic fault","Confirm the instrument diagnostic and follow the approved maintenance protocol.")
    thresholds=[("AvgSS",lambda v:v<40,"fault","Very low optical signal"),("AvgSS",lambda v:40<=v<70,"warning","Low optical signal"),("DeltaSS",lambda v:abs(v)>5,"warning","Uneven optical contamination"),("Cooler",lambda v:v>2.6 or v<0.05,"warning","Detector cooler outside usual range"),("Pres",lambda v:v<50 or v>110,"warning","Cell pressure outside usual range"),("CO2MF",lambda v:v<250 or v>1200,"warning","CO₂ outside usual ambient range"),("RSSI",lambda v:v<10,"fault","Very low LI-7700 signal"),("RSSI",lambda v:10<=v<20,"warning","Low LI-7700 signal"),("Vin",lambda v:0<v<11.5,"fault","Low SmartFlux supply voltage"),("NumSat",lambda v:v<4,"warning","Few GPS satellites"),("AnemDiag",lambda v:v!=0,"warning","Sonic diagnostic flag"),("DropRate",lambda v:v>5,"warning","High LI-7700 drop rate")]
    if enclosed:
        thresholds += [("MeasFlowRate",lambda v:v<1,"fault","No analyzer flow"),("MeasFlowRate",lambda v:1<=v<10,"warning","Low analyzer flow"),("FlowDrive",lambda v:v>90,"warning","High pump drive"),("DPres",lambda v:abs(v)>6,"warning","Large cell pressure drop")]
    for tag,test,severity,title in thresholds:
        if tag in measured and test(measured[tag]):
            issue(severity,title,f"{METRICS[tag][0]}: {measured[tag]:g} {METRICS[tag][1]}. Check the corresponding maintenance protocol.")
    usb = {key:number(values.get("Info/USB/"+key)) for key in ["State","Size","Free"]}
    if usb["State"] in {0,3}:
        issue("fault","Logging drive unavailable" if usb["State"]==0 else "Logging drive error","Inspect the logging drive at the next authorized maintenance check.")
    elif usb["State"]==2:
        issue("warning","Logging drive idle","Confirm that recording is expected to be running.")
    if usb["Free"] is not None:
        if usb["Free"]<200:
            issue("fault","Logging drive nearly full",f"{usb['Free']:g} MB free.")
        elif usb["Size"] and usb["Free"]/usb["Size"]<0.15:
            issue("warning","Logging drive below 15% free","Plan a drive service visit.")
    last_file=values.get("Fluxes/Status/EddyPro/LastFile", "")
    age=None
    match=re.search(r"(\d{4}-\d{2}-\d{2})T(\d{6})", last_file)
    if match:
        try:
            stamp=datetime.strptime("".join(match.groups()),"%Y-%m-%d%H%M%S").replace(tzinfo=timezone(timedelta(hours=utc_offset)))
            age=(datetime.now(timezone.utc)-stamp).total_seconds()/60
            if age>180:
                issue("fault","SmartFlux file more than 3 hours old",f"Latest reported file age: {age:.0f} minutes.")
            elif age>75:
                issue("warning","SmartFlux file more than 75 minutes old",f"Latest reported file age: {age:.0f} minutes.")
            elif age < -5:
                issue("warning","SmartFlux clock appears ahead","Confirm the logger time basis in the private station configuration.")
        except ValueError:
            pass
    has_data=any(k.startswith("Data/") for k in values) and any(tag in measured for tag in ("CO2MF","CO2D","H2OMF","H2OD","U","CH4"))
    if not has_data:
        issue("fault","No measurement record returned","The analyzer may answer status queries without returning measurements. No settings were changed.")
    if inferred:
        issue("note","Label-less data inferred from output settings","Field order was reconstructed from the enabled Ethernet outputs; verify against labelled output.")
    rank={"fault":3,"warning":2,"note":1}
    issues.sort(key=lambda i:rank[i["severity"]],reverse=True)
    status="fault" if any(i["severity"]=="fault" for i in issues) else "warning" if any(i["severity"]=="warning" for i in issues) else "healthy" if has_data else "no_data"
    return {"status":status,"has_data":has_data,"model":model[:150],"serial":values.get("Coef/Current/SerialNo", "")[:100],"firmware":values.get("EmbeddedSW/Version", "")[:60],"metrics":[{"tag":tag,"value":value,"label":METRICS[tag][0],"unit":METRICS[tag][1],"group":METRICS[tag][2]} for tag,value in measured.items()],"issues":issues,"flags":flags,"diagnostic_word":int(diag_value) if diag_value is not None else None,"usb":usb,"smartflux":{"model":values.get("Fluxes/Status/SmartFlux/Model", "")[:100],"run_status":values.get("Fluxes/Status/EddyPro/RunStatus", "")[:80],"last_file":last_file[:200],"file_age_minutes":round(age,1) if age is not None else None},"calibrations":{tag:values.get("Calibrate/"+tag+"/Date", "")[:80] for tag in ["ZeroCO2","SpanCO2","ZeroH2O","SpanH2O"]}}


def poll(host, port=7200, timeout=6, utc_offset=-5):
    """One bounded, read-only connection. All writes go through one guard."""
    deadline=time.monotonic()+timeout
    records, raw_lines, buffer, line_buffer=[],[],"",""
    with socket.create_connection((host, port), timeout=timeout) as client:
        for query in QUERIES:
            client.sendall(read_only_query(query))
        total=0
        while time.monotonic()<deadline:
            client.settimeout(min(0.4,max(0.01,deadline-time.monotonic())))
            try:
                data=client.recv(32768)
            except socket.timeout:
                if any(r.startswith("(Data") for r in records) and any(r.startswith("(FlowBox") for r in records) and any(r.startswith("(Fluxes") for r in records):
                    break
                continue
            if not data:
                break
            total+=len(data)
            if total>512*1024:
                break
            chunk=data.decode("utf-8",errors="replace")
            line_buffer+=chunk
            lines=line_buffer.split("\n")
            line_buffer=lines.pop()[-262144:]
            buffer+=chunk
            complete,buffer=split_records(buffer)
            records.extend(complete)
            raw_lines.extend(line for line in lines if re.fullmatch(r"[\d.eE+\-\s]+",line) and len(line.split())>=3)
            if len(buffer)>262144:
                raise ValueError("Unframed instrument response")
    return decode(records,raw_lines,utc_offset)
