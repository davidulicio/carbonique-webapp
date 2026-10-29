"""Server-authoritative, retry-safe field operations and append-only audit records."""
import hashlib
import json
import uuid
from datetime import datetime
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import APIException, ValidationError
from inventory.models import Equipment
from .models import AuditEvent, OperationReceipt, Task, TaskActivity, Visit, VisitObservation, DataCaveat
from .permissions import require_role, require_site, display_name
from .reports import close_report
from .serializers import TaskSerializer, VisitSerializer, clean_html

class Conflict(APIException):
    status_code = 409
    default_detail = "The record changed on another device. Review the current version before retrying."

def audit(user, action, obj, site=None, detail=None):
    AuditEvent.objects.create(actor=user, actor_name=display_name(user), action=action, entity_type=obj._meta.label_lower, entity_id=str(obj.pk), site=site, detail=detail or {})

def entity_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("Use a valid UUID for the operation and record identifiers.")

def event_time(value):
    if not value:
        return timezone.now()
    parsed = parse_datetime(str(value))
    if not parsed or timezone.is_naive(parsed):
        raise ValidationError("Timestamps must include a UTC offset.")
    return parsed

def nonempty(value, label, limit):
    value = str(value or "").strip()
    if not value or len(value) > limit:
        raise ValidationError(f"{label} is required and must be at most {limit} characters.")
    return value

def optional_date(value):
    if not value:
        return None
    date = parse_date(str(value))
    if not date:
        raise ValidationError("Use a date in YYYY-MM-DD format.")
    return date

def same_site_visit(site, value, open_only=True):
    if not value:
        return None
    try:
        visit = Visit.objects.select_for_update().get(pk=entity_uuid(value), site=site)
    except Visit.DoesNotExist:
        raise ValidationError("The linked visit does not exist at this site.")
    if open_only and visit.status != "open":
        raise Conflict("This visit is closed. Reopen it to add a correction; previous reports are retained.")
    return visit

def check_version(obj, value):
    if value is None:
        raise ValidationError("base_version is required for edits.")
    try:
        current = int(value)
    except (ValueError, TypeError):
        raise ValidationError("base_version must be an integer.")
    if current != obj.version:
        raise Conflict({"message": "This record changed on another device.", "current_version": obj.version, "entity_id": str(obj.pk)})

@transaction.atomic
def apply_operation(user, operation):
    require_role(user, "member", "researcher", "manager", "admin")
    if not isinstance(operation, dict):
        raise ValidationError("An operation must be a JSON object.")
    operation_id = entity_uuid(operation.get("id"))
    digest = hashlib.sha256(json.dumps(operation, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # Lock the actor to serialize retries and prevent duplicate receipt races.
    user.__class__.objects.select_for_update().get(pk=user.pk)
    receipt = OperationReceipt.objects.filter(actor=user, operation_id=operation_id).first()
    # Retries may read archived sites, but revoked access must never replay data.
    require_site(user, operation.get("site_id"))
    if receipt:
        if receipt.payload_hash != digest:
            raise Conflict("An operation identifier cannot be reused with different content.")
        return receipt.result
    site = require_site(user, operation.get("site_id"), writable=True)
    kind = operation.get("kind", "")
    if not isinstance(kind, str):
        raise ValidationError("The operation kind must be a string.")
    payload = operation.get("payload", {})
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object.")
    record_id = entity_uuid(operation.get("entity_id"))
    occurred_at = event_time(operation.get("occurred_at"))
    name = display_name(user)
    result = {"id": str(operation_id), "ok": True, "entity_id": str(record_id)}

    if kind == "visit.create":
        if Visit.objects.filter(pk=record_id).exists():
            raise Conflict("A visit already uses this identifier.")
        date = parse_date(str(payload.get("date", "")))
        if not date:
            raise ValidationError("A visit date is required (YYYY-MM-DD).")
        classification = payload.get("classification", "routine")
        if classification not in {"routine", "major", "fault"}:
            raise ValidationError("Unknown visit classification.")
        visit = Visit.objects.create(id=record_id, site=site, date=date, crew=str(payload.get("crew", name))[:500], title=str(payload.get("title", ""))[:250], classification=classification, started_at=occurred_at, created_by=user)
        result["record"] = VisitSerializer(visit).data
        audit(user, kind, visit, site)
    elif kind.startswith("visit."):
        visit = same_site_visit(site, record_id, open_only=False)
        check_version(visit, operation.get("base_version"))
        if kind == "visit.close":
            if visit.status != "open":
                raise Conflict("The visit is already closed.")
            if occurred_at < visit.started_at:
                raise ValidationError("Visit end precedes its start. Correct the device clock or edit the recorded start before closing the visit.")
            visit.status, visit.ended_at = "closed", occurred_at
            visit.version += 1
            visit.save()
            close_report(visit, user)
        elif kind == "visit.reopen":
            if visit.status != "closed":
                raise Conflict("The visit is already open.")
            visit.status, visit.ended_at = "open", None
            visit.version += 1
            visit.save()
        elif kind == "visit.edit":
            if visit.status != "open":
                raise Conflict("Reopen this visit before correcting its notes.")
            if "date" in payload:
                date = parse_date(str(payload["date"]))
                if not date:
                    raise ValidationError("Invalid visit date.")
                visit.date = date
            for key, limit in [("crew", 500), ("title", 250)]:
                if key in payload:
                    setattr(visit, key, str(payload[key])[:limit])
            if "classification" in payload:
                if payload["classification"] not in {"routine", "major", "fault"}:
                    raise ValidationError("Invalid classification.")
                visit.classification = payload["classification"]
            if "started_at" in payload:
                visit.started_at = event_time(payload["started_at"])
            if "narrative" in payload:
                visit.narrative = clean_html(str(payload["narrative"]))
            visit.version += 1
            visit.save()
        else:
            raise ValidationError("Unknown visit operation.")
        result["record"] = VisitSerializer(visit).data
        audit(user, kind, visit, site, {"version": visit.version})
    elif kind == "observation.create":
        visit = same_site_visit(site, payload.get("visit_id"))
        if visit is None:
            raise ValidationError("A visit is required.")
        if VisitObservation.objects.filter(pk=record_id).exists():
            raise Conflict("An observation already uses this identifier.")
        note = VisitObservation.objects.create(id=record_id, visit=visit, text=nonempty(payload.get("text"), "Observation", 20000), author=user, author_name=name, occurred_at=occurred_at)
        from .serializers import VisitObservationSerializer
        result["record"] = VisitObservationSerializer(note).data
        audit(user, kind, note, site)
    elif kind.startswith("task."):
        activity_id = entity_uuid(payload["activity_id"]) if payload.get("activity_id") else uuid.uuid4()
        if TaskActivity.objects.filter(pk=activity_id).exists():
            raise Conflict("Another task activity already uses this identifier.")
        visit = same_site_visit(site, payload.get("visit_id"))
        text = str(payload.get("text", ""))[:20000]
        if kind == "task.create":
            if Task.objects.filter(pk=record_id).exists():
                raise Conflict("A task already uses this identifier.")
            priority = payload.get("priority", "normal")
            if priority not in {"normal", "high"}:
                raise ValidationError("Invalid priority.")
            equipment = None
            if payload.get("equipment_id"):
                try:
                    equipment = Equipment.objects.filter(pk=payload["equipment_id"]).first()
                except (ValueError, TypeError):
                    raise ValidationError("Invalid equipment identifier.")
                if not equipment or equipment.site_id not in (None, site.pk):
                    raise ValidationError("Select equipment at this site or in storage.")
            due_date = optional_date(payload.get("due_date"))
            task = Task.objects.create(id=record_id, site=site, equipment=equipment, title=nonempty(payload.get("title"), "Task title", 250), details=str(payload.get("details", ""))[:20000], priority=priority, due_date=due_date, created_visit=visit, created_by=user, created_at=occurred_at)
            action = "created"
        else:
            try:
                task = Task.objects.select_for_update().get(pk=record_id, site=site)
            except Task.DoesNotExist:
                raise ValidationError("This task does not exist at the selected site.")
            if kind == "task.comment":
                text = nonempty(payload.get("text"), "Comment", 20000)
                action = "commented"
            else:
                check_version(task, operation.get("base_version"))
                if kind == "task.complete":
                    if visit is None:
                        raise ValidationError("Select an open visit before completing work.")
                    if task.status != "pending":
                        raise Conflict("Only a pending task can be completed.")
                    task.status, action = "done", "completed"
                elif kind == "task.reopen":
                    task.status, action = "pending", "reopened"
                elif kind == "task.archive":
                    if task.created_by_id != user.pk:
                        require_role(user, "admin")
                    task.status, action = "archived", "archived"
                elif kind == "task.edit":
                    if "title" in payload:
                        task.title = nonempty(payload["title"], "Title", 250)
                    if "details" in payload:
                        task.details = str(payload["details"])[:20000]
                    if "priority" in payload:
                        if payload["priority"] not in {"normal", "high"}:
                            raise ValidationError("Invalid priority.")
                        task.priority = payload["priority"]
                    if "due_date" in payload:
                        task.due_date = optional_date(payload["due_date"])
                    action = "edited"
                else:
                    raise ValidationError("Unknown task operation.")
                task.version += 1
                task.save()
        activity = TaskActivity.objects.create(id=activity_id, task=task, visit=visit, action=action, task_title=task.title, text=text, author=user, author_name=name, occurred_at=occurred_at)
        from .serializers import TaskActivitySerializer
        result["activity"] = TaskActivitySerializer(activity).data
        result["activity_id"] = str(activity_id)
        result["record"] = TaskSerializer(task).data
        audit(user, kind, task, site, {"version": task.version})
    elif kind in {'calibration.create', 'calibration.edit'}:
        from .record_resources import save_calibration, CalibrationSerializer
        obj = save_calibration(user, site, record_id, payload, create=kind == 'calibration.create', base_version=operation.get('base_version'))
        result['record'] = json.loads(json.dumps(CalibrationSerializer(obj).data, default=str))
    elif kind == "caveat.draft":
        visit = same_site_visit(site, payload.get("visit_id"))
        if DataCaveat.objects.filter(pk=record_id).exists():
            raise Conflict("A caveat already uses this identifier.")
        caveat = DataCaveat.objects.create(id=record_id, source_visit=visit, title=nonempty(payload.get("title"), "Title", 300), description=clean_html(str(payload.get("description", ""))), variables=str(payload.get("variables", ""))[:500], period_label=str(payload.get("period_label", ""))[:500], created_by=user)
        caveat.sites.add(site)
        from .serializers import CaveatSerializer
        result["record"] = CaveatSerializer(caveat, context={"user": user}).data
        audit(user, kind, caveat, site)
    else:
        raise ValidationError("Unknown field operation.")
    # JSON serialization normalizes UUIDs/dates before storing receipts.
    from rest_framework.renderers import JSONRenderer
    result = json.loads(JSONRenderer().render(result))
    OperationReceipt.objects.create(operation_id=operation_id, actor=user, payload_hash=digest, result=result)
    return result
