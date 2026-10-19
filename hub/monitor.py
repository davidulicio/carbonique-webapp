"""Private VM configuration, bounded polling and site-scoped display API."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import TowerStatus, TowerReading
from .permissions import accessible_sites, require_site
from .resources_api import team_access
from . import licor


def configured_stations():
    path = getattr(settings, "MONITOR_STATIONS_FILE", "")
    if not path:
        return {}, "not_configured"
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError()
        output = {}
        for code, entry in data.items():
            if not isinstance(entry, dict) or not isinstance(entry.get("host"),str) or not entry["host"].strip():
                raise ValueError()
            port, offset = int(entry.get("port",7200)), float(entry.get("utc_offset",-5))
            if not 1 <= port <= 65535 or not -12 <= offset <= 14:
                raise ValueError()
            output[str(code).upper()] = {"host":entry["host"].strip(),"port":port,"utc_offset":offset}
        return output, ""
    except (OSError, ValueError, TypeError):
        # Do not expose file paths, target addresses, or configuration contents.
        return {}, "configuration_error"


def collect(sites):
    stations, config_error = configured_stations()
    now=timezone.now()
    cooldown=max(15,int(getattr(settings,"MONITOR_MIN_INTERVAL",30)))
    timeout=min(15,max(1,float(getattr(settings,"MONITOR_TIMEOUT",6))))
    work={}
    for site in sites:
        obj,_=TowerStatus.objects.get_or_create(site=site)
        config=stations.get(site.code.upper())
        if not config:
            obj.status=config_error or "not_configured"
            obj.save(update_fields=["status"])
            continue
        # Conditional UPDATE works across Gunicorn workers, including SQLite.
        cutoff=now-timedelta(seconds=cooldown)
        from django.db.models import Q
        claimed=TowerStatus.objects.filter(pk=obj.pk).filter(Q(attempted_at__isnull=True)|Q(attempted_at__lt=cutoff)).update(attempted_at=now)
        if claimed:
            work[site.pk]=(obj,config)
    if not work:
        return
    with ThreadPoolExecutor(max_workers=min(6,len(work))) as executor:
        futures={executor.submit(licor.poll,config["host"],config["port"],timeout,config["utc_offset"]):obj for obj,config in work.values()}
        for future in as_completed(futures):
            obj=futures[future]
            try:
                result=future.result()
                obj.status=result["status"]
                obj.payload=result
                if result["has_data"]:
                    obj.observed_at=timezone.now()
                    obj.last_good=result
                    TowerReading.objects.create(site=obj.site,observed_at=obj.observed_at,metrics={m["tag"]:m["value"] for m in result["metrics"]})
            except (OSError,TimeoutError):
                obj.status="unreachable"
            except (ValueError,KeyError,TypeError):
                obj.status="invalid_response"
            obj.save(update_fields=["status","payload","observed_at","last_good"])


MESSAGES={"not_configured":"Tower connection has not been configured on the VM.","configuration_error":"Private monitor configuration needs server administrator attention.","not_checked":"No check has been run yet.","unreachable":"The VM could not reach the analyzer. Check power, network routing and VPN connectivity.","invalid_response":"The analyzer response could not be interpreted. No instrument settings were changed."}


def display_status(site, obj=None, history=False):
    obj=obj or TowerStatus.objects.filter(site=site).first()
    status=obj.status if obj else "not_checked"
    data=(obj.payload if obj.payload.get("has_data") else obj.last_good) if obj else {}
    stale=not obj or not obj.observed_at or (timezone.now()-obj.observed_at).total_seconds()>getattr(settings,"MONITOR_STALE_SECONDS",300)
    # A failed connection never displays the earlier healthy state as current.
    issues=list(obj.payload.get("issues",[])) if obj and status not in MESSAGES else []
    if status in MESSAGES:
        issues.insert(0,{"severity":"fault" if status in {"unreachable","invalid_response"} else "note","title":status.replace("_"," ").capitalize(),"detail":MESSAGES[status]})
    if stale and data:
        issues.insert(0,{"severity":"warning","title":"Earlier measurement snapshot","detail":"Displayed measurements are from the last successful check, not a current live feed."})
    output={"site":site.pk,"code":site.code,"name":site.name,"status":"stale" if stale and status=="healthy" else status,"checked_at":obj.attempted_at if obj else None,"observed_at":obj.observed_at if obj else None,"stale":stale,"last_known":bool(data) and (status in MESSAGES or not obj.payload.get("has_data")),"issues":issues,"data":data}
    if history:
        cutoff=timezone.now()-timedelta(hours=24)
        output["history"]=[{"at":r.observed_at,"metrics":r.metrics} for r in site.tower_readings.filter(observed_at__gte=cutoff).order_by("-observed_at")[:240]][::-1]
    return output


@api_view(["GET"])
def tower_status(request):
    team_access(request.user)
    selected=request.query_params.get("site")
    sites=[require_site(request.user,selected)] if selected else list(accessible_sites(request.user).filter(is_archived=False).order_by("code"))
    if request.query_params.get("refresh")=="1":
        collect(sites)
    stations, config_error=configured_stations()
    statuses={o.site_id:o for o in TowerStatus.objects.filter(site__in=sites)}
    output=[]
    for site in sites:
        data=display_status(site,statuses.get(site.pk),history=bool(selected))
        if site.code.upper() not in stations:
            data.update(status=config_error or "not_configured", stale=True)
        output.append(data)
    response=Response({"towers":output,"server_time":timezone.now(),"read_only":True,"min_interval_seconds":max(15,getattr(settings,"MONITOR_MIN_INTERVAL",30)),"stale_after_seconds":getattr(settings,"MONITOR_STALE_SECONDS",300)})
    response["Cache-Control"]="private, no-store"
    return response
