"""Explicit public projection of current sites, visits and all caveat statuses."""
import base64
import json
import re
import math
from datetime import timedelta, timezone as datetime_timezone
from functools import lru_cache

from django.conf import settings
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from inventory.models import Site
from .models import Attachment, DataCaveat, Deployment, ImportRecord, ProcessingFile, Visit
from .serializers import clean_html


def logger_time(value):
    return value.astimezone(datetime_timezone(timedelta(hours=-5))).strftime("%Y-%m-%d %H:%M") if value else ""


def geometry(site):
    points = []
    def number(value):
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*(m|cm)?\b", str(value), re.I)
        if not match:
            return None
        value = float(match[1]) / (100 if (match[2] or "").lower() == "cm" else 1)
        return value if value >= 0 and math.isfinite(value) else None
    def add(value, label, kind="other"):
        height = number(value)
        if height is not None:
            points.append({"height": height, "label": label, "kind": kind})
    now = timezone.now()
    for deployment in site["deployments"]:
        if deployment["height"] is not None and deployment["installed_at"] <= now and (not deployment["removed_at"] or deployment["removed_at"] > now):
            add(deployment["height"], deployment["instrument"], "current")
    if not points:
        for section in site["sections"]:
            for group in section["groups"]:
                name = group["heading"].lower()
                for item in group["items"]:
                    key, value = item["key"], item["value"]
                    if "sonic anemometer" in name and key.lower().startswith("sonic height"):
                        add(value, "EC (sonic)", "ec")
                    elif "temperature and humidity" in name and re.search(r"TA_\d+_\d+_\d+", key):
                        add(value, re.search(r"TA_\d+_\d+_\d+", key)[0], "ta")
                    elif any(term in name for term in ["wind monitor", "net radiometer", "snow"]) and key.lower().startswith("height"):
                        add(value, group["heading"])
                    elif "profile system" in name and "intake heights" in key.lower():
                        for height in re.findall(r"\d+(?:\.\d+)?", value):
                            add(height, "Profile intake")
    if not points:
        return None
    points.sort(key=lambda point: -point["height"])
    bottom = max(270, 65 + len(points) * 20)
    maximum = max(1, max(point["height"] for point in points)) * 1.12
    y = lambda height: bottom - height / maximum * (bottom - 25)
    for index, point in enumerate(points):
        point["y"] = y(point["height"])
        point["label_y"] = max(point["y"], points[index-1]["label_y"] + 18 if index else 30)
    for index in range(len(points)-1, -1, -1):
        points[index]["label_y"] = min(points[index]["label_y"], bottom-5 if index == len(points)-1 else points[index+1]["label_y"]-18)
    ec = next((point for point in points if point["kind"] == "ec"), None)
    ta = [point for point in points if point["kind"] == "ta"]
    closest = min(ta, key=lambda point: abs(point["height"]-ec["height"])) if ec and ta else None
    return {"points": points, "bottom": bottom, "height": bottom+25, "closest": closest,
        "ticks": [{"height": round(maximum*i/4, 1), "y": y(maximum*i/4)} for i in range(5)]}


def sections(value):
    """Copy only the documented reference structure, never arbitrary metadata."""
    result = []
    for section in value if isinstance(value, list) else []:
        if not isinstance(section, dict):
            continue
        items = lambda rows: [{"key": str(i.get("k", "")), "value": str(i.get("v", ""))}
            for i in rows if isinstance(i, dict)] if isinstance(rows, list) else []
        result.append({"heading": str(section.get("h", "")), "items": items(section.get("items")),
            "groups": [{"heading": str(group.get("h", "")), "items": items(group.get("items"))}
                for group in section.get("subs", []) if isinstance(group, dict)]
                if isinstance(section.get("subs", []), list) else []})
    return result


def image_uri(field):
    """Only known imported scientific images are eligible for embedding."""
    try:
        with field.open("rb") as handle:
            data = handle.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            return None
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            mime = "image/png"
        elif data.startswith(b'\xff\xd8\xff'):
            mime = "image/jpeg"
        else:
            return None
        return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=1)
def assets():
    root = settings.BASE_DIR / "static/hub"
    fonts = (root / "fonts.css").read_text(encoding="utf-8")
    def font(match):
        filename = match.group(1)
        data = (root / "fonts" / filename).read_bytes()
        return "url(data:font/ttf;base64," + base64.b64encode(data).decode("ascii") + ")"
    fonts = re.sub(r"url\(\./fonts/([\w.-]+)\)", font, fonts)
    notices = '\n'.join(path.read_text(encoding='utf-8') for path in (root/'fonts').glob('*-OFL.txt'))
    return {
        "css": '/* Bundled font licenses\n'+notices.replace('*/','* /')+'\n*/\n'+fonts + "\n" + (root / "public-report.css").read_text(encoding="utf-8"),
        "script": (root / "public-report.js").read_text(encoding="utf-8"),
        "logo": "data:image/svg+xml;base64," + base64.b64encode((root / "logo.svg").read_bytes()).decode("ascii"),
    }


def timeline_data(sites, visits, caveats):
    """Project current public records without inventing measurement dates."""
    rows = {site['id']: {'id': site['id'], 'code': site['code'], 'dated': [], 'undated': []} for site in sites}
    for visit in visits:
        rows[visit['site_id']]['dated'].append({
            'target': 'visit-'+visit['id'], 'record_kind': 'visit', 'kind': visit['classification'],
            'status': '', 'date': visit['date'].isoformat(), 'label': visit['kind'],
            'title': visit['title'], 'detail': visit['crew'], 'site': visit['site'],
        })
    for caveat in caveats:
        date = (caveat['affected_from'] or caveat['affected_to']).split(' ')[0]
        basis = 'Affected start (fixed EST)' if caveat['affected_from'] else 'Affected end (fixed EST)' if caveat['affected_to'] else 'Affected dates not recorded'
        status = 'Draft · awaiting review' if caveat['status'] == 'draft' else caveat['status_label']
        for site_id in caveat['site_ids']:
            if site_id not in rows:
                continue
            rows[site_id]['dated' if date else 'undated'].append({
                'target': 'caveat-'+caveat['id'], 'record_kind': 'caveat', 'kind': 'caveat',
                'status': caveat['status'], 'date': date, 'label': 'Data caveat · '+status,
                'title': caveat['title'], 'detail': basis+(' · '+caveat['period'] if caveat['period'] else ''),
                'site': rows[site_id]['code'],
            })
    entries = [entry for row in rows.values() for section in ['dated', 'undated'] for entry in row[section]]
    return {'rows': list(rows.values()), 'has_entries': bool(entries), 'visits': len(visits),
        'caveats': len({entry['target'] for entry in entries if entry['record_kind'] == 'caveat'})}


def context():
    sites = list(Site.objects.select_related("condition").order_by("code"))
    site_ids = [site.pk for site in sites]
    visits = list(Visit.objects.filter(site_id__in=site_ids).select_related("site")
        .prefetch_related("observations", "task_activities").order_by("-date", "-started_at", "pk"))
    caveats = list(DataCaveat.objects.prefetch_related("sites").order_by("-updated_at", "pk"))
    caveat_ids = {c.pk for c in caveats}
    # A caveat does not expose arbitrary uploaded files. Imported
    # figures already belonged to the supplied public scientific reference.
    source_ids = set(ImportRecord.objects.filter(source="fieldnotes-media", entity_type="hub.attachment")
        .values_list("entity_id", flat=True))
    images = Attachment.objects.filter(pk__in=source_ids, site_id__in=site_ids).order_by("created_at", "pk")
    photos, plots, seen_photos, seen_plots = {}, {}, set(), set()
    image_cache = {}
    for item in images:
        if item.configuration_id or item.visit_id or item.equipment_id:
            continue
        if item.caveat_id and item.caveat_id not in caveat_ids:
            continue
        key = (item.caveat_id or item.site_id, item.sha256)
        seen = seen_plots if item.caveat_id else seen_photos
        if key in seen:
            continue
        seen.add(key)
        if item.sha256 not in image_cache:
            image_cache[item.sha256] = image_uri(item.file)
        uri = image_cache[item.sha256]
        if uri:
            target, pk = (plots, item.caveat_id) if item.caveat_id else (photos, item.site_id)
            target.setdefault(pk, []).append({"src": uri, "caption": item.caption})

    public_sites, common, common_seen = [], [], set()
    for site in sites:
        metadata = site.metadata if isinstance(site.metadata, dict) else {}
        reference = metadata.get("reference", {})
        reference = reference if isinstance(reference, dict) else {}
        current_sections = sections(reference.get("sections"))
        # Canonical editable fields override older labels in the imported source.
        canonical = {"Site name": site.name, "AmeriFlux ID": site.amp,
            "Location": site.location, "Coordinates": site.gps_coordinates,
            "Station active since": site.date_activated.isoformat()}
        for section in current_sections:
            if section["heading"].lower() == "site info":
                for item in section["items"]:
                    if item["key"] in canonical:
                        item["value"] = canonical[item["key"]]
        for block in metadata.get("common", []) if isinstance(metadata.get("common"), list) else []:
            if not isinstance(block, dict):
                continue
            normalized = {"title": str(block.get("title", "Common setup")), "sections": sections(block.get("sections"))}
            key = json.dumps(normalized, sort_keys=True)
            if key not in common_seen:
                common.append(normalized)
                common_seen.add(key)
        condition = getattr(site, 'condition', None)
        public_condition = {'status': condition.status if condition else 'unknown',
            'label': condition.get_status_display() if condition else 'Not assessed',
            'statement': condition.statement if condition else '',
            'valid_until': condition.valid_until if condition else None,
            'updated_at': condition.updated_at if condition else None,
            'review_overdue': bool(condition and condition.valid_until and condition.valid_until < timezone.localdate())}
        public_sites.append({"id": site.pk, "code": site.code, "name": site.name, "amp": site.amp,
            "condition": public_condition,
            "location": site.location, "coordinates": site.gps_coordinates,
            "active_since": site.date_activated, "archived": site.is_archived, "description": clean_html(site.description),
            "sections": current_sections, "photos": photos.get(site.pk, []), "deployments": []})
    by_id = {site["id"]: site for site in public_sites}
    for deployment in Deployment.objects.filter(site_id__in=site_ids).select_related("equipment").order_by("installed_at"):
        by_id[deployment.site_id]["deployments"].append({"instrument": deployment.equipment.instrument,
            "model": deployment.equipment.model_number, "height": deployment.height_m, "depth": deployment.depth_m,
            "variables": deployment.variables, "installed_at": deployment.installed_at, "removed_at": deployment.removed_at})
    for site in public_sites:
        site["diagram"] = geometry(site)

    public_visits = [{"id": str(visit.pk), "site_id": visit.site_id, "site": visit.site.code,
        "date": visit.date, "title": visit.title or "Field visit", "crew": visit.crew,
        "classification": visit.classification, "kind": visit.get_classification_display(),
        "status": visit.status, "narrative": clean_html(visit.narrative),
        "observations": [{"text": item.text} for item in visit.observations.all()],
        "work": [{"title": item.task_title, "text": item.text} for item in visit.task_activities.all()
            if item.action == "completed"]} for visit in visits]
    public_caveats = []
    for caveat in caveats:
        evidence = caveat.evidence if isinstance(caveat.evidence, dict) else {}
        links = []
        for link in evidence.get("links", []) if isinstance(evidence.get("links"), list) else []:
            if isinstance(link, dict) and re.match(r"^https?://[^\s]+$", str(link.get("u", "")), re.I):
                links.append({"url": link["u"], "title": str(link.get("t", "Source"))})
        public_caveats.append({"id": str(caveat.pk), "title": caveat.title,
            "sites": [site.code for site in caveat.sites.all() if site.pk in by_id],
            "site_ids": [site.pk for site in caveat.sites.all() if site.pk in by_id],
            "description": clean_html(caveat.description), "treatment": clean_html(caveat.treatment),
            "status": caveat.status, "status_label": caveat.get_status_display(), "variables": caveat.variables,
            "period": caveat.period_label, "affected_from": logger_time(caveat.affected_from), "affected_to": logger_time(caveat.affected_to),
            "reviewed_at": caveat.reviewed_at, "resolved_at": caveat.resolved_at, "updated_at": caveat.updated_at,
            "cross_check": clean_html(str(evidence.get("xref", ""))),
            "needs_confirmation": clean_html(str(evidence.get("flag", ""))),
            "plots": plots.get(caveat.pk, []), "links": links})
    # Only current scientific INI files for known sites and shared include files
    # enter the report; internal notes, actors and version history stay private.
    ini_files = []
    for document in ProcessingFile.objects.filter(Q(site_id__in=site_ids)|Q(site_code='')).prefetch_related('revisions'):
        version=next(iter(document.revisions.all()),None)
        if not version:
            continue
        try:
            with version.file.open('rb') as handle:
                raw=handle.read()
            from .processing_files import decoded
            text=decoded(raw)
        except (OSError,ValueError):
            continue
        name=document.path.rsplit('/',1)[-1]
        ini_files.append({'filename':name,'site':document.site_code or 'Shared include',
            'stage':f'Version {version.revision}','summary':'Current INI library version.',
            'text':text,'bytes':base64.b64encode(raw).decode('ascii')})
    # Compatibility for an installation that has not imported the new library yet.
    mappings=ImportRecord.objects.filter(source="inventory-export", source_id__startswith="ini:") if not ProcessingFile.objects.exists() else []
    for mapping in mappings:
        data = mapping.payload
        if not isinstance(data, dict) or str(data.get("s", "")).upper() not in {site.code.upper() for site in sites}:
            continue
        name = str(data.get("f", ""))
        if name != name.replace("\\", "/").split("/")[-1] or not name.endswith(".ini"):
            continue
        path = settings.BASE_DIR / "seed/ecoflux_inventory_export/ini" / name
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig")
        except (OSError, UnicodeError):
            continue
        ini_files.append({"filename": name, "site": str(data.get("s", "")),
            "stage": str(data.get("st", "")), "summary": str(data.get("sum", "")), "text": text,
            "bytes":base64.b64encode(raw).decode('ascii')})
    return {"sites": public_sites, "visits": public_visits, "caveats": public_caveats,
        "timeline": timeline_data(public_sites, public_visits, public_caveats),
        "resolved": [item for item in public_caveats if item["status"] == "resolved"],
        "open_caveats": [item for item in public_caveats if item["status"] != "resolved"],
        "common": common, "ini_files": ini_files, "generated_at": timezone.now(), **assets()}


def render_report(*, snapshot=False):
    data = context()
    data["is_snapshot"] = snapshot
    return render_to_string("public_report.html", data)
