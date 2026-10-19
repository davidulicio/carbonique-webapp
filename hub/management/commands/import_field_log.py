import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from inventory.models import Site
from hub.models import Task, TaskActivity, Visit, VisitObservation, VisitReport, ImportRecord
from hub.reports import render_visit_report

def stamp(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CommandError("Imported timestamps must include a timezone.")
    return parsed

def stable(kind, site, value):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"carbonique-firestore:{site}:{kind}:{value}")

class Command(BaseCommand):
    help = "Import the normalized JSON produced by scripts/export_firestore.py, using an explicit site map."
    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--site-map", required=True, help='JSON file mapping Firebase site IDs to canonical codes, e.g. {"firebase-id": "UQAM_3"}')
    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(Path(options["file"]).read_text(encoding="utf-8-sig"))
        mapping = json.loads(Path(options["site_map"]).read_text(encoding="utf-8-sig"))
        count = 0
        for source in data.get("sites", []):
            sid = source["id"]
            if sid not in mapping:
                raise CommandError(f"No canonical site mapping for Firebase site {sid} ({source.get('name', '')}).")
            site = Site.objects.filter(code__iexact=mapping[sid]).first()
            if not site:
                raise CommandError(f"Canonical site {mapping[sid]} does not exist.")
            visits = {}
            for v in source.get("visits", []):
                source_id = f"{sid}:visit:{v['id']}"
                visit, created = Visit.objects.get_or_create(id=stable("visit", sid, v["id"]), defaults={"site": site, "date": v["date"], "crew": v.get("crew", ""), "status": v.get("status", "closed"), "started_at": stamp(v.get("startedAt")) or stamp(v["date"]+"T12:00:00-05:00"), "ended_at": stamp(v.get("endedAt")), "created_by": get_user_model().objects.filter(email__iexact=v.get("startedByEmail", "")).first(), "title": "Imported Field Log visit"})
                visits[v["id"]] = visit
                if created:
                    ImportRecord.objects.create(source="field-log", source_id=source_id, entity_type="hub.visit", entity_id=str(visit.pk), payload=v)
                    count += 1
            tasks = {}
            for t in source.get("tasks", []):
                source_id = f"{sid}:task:{t['id']}"
                task, created = Task.objects.get_or_create(id=stable("task", sid, t["id"]), defaults={"site": site, "title": t["title"], "details": t.get("details", ""), "status": t.get("status", "pending"), "priority": t.get("priority", "normal"), "created_visit": visits.get(t.get("createdVisitId")), "created_by": get_user_model().objects.filter(email__iexact=t.get("createdByEmail", "")).first(), "created_at": stamp(t.get("createdAt")) or datetime.now(timezone.utc)})
                tasks[t["id"]] = task
                if created:
                    TaskActivity.objects.create(id=stable("created", sid, t["id"]), task=task, visit=visits.get(t.get("createdVisitId")), action="created", task_title=t["title"], author_name=t.get("createdBy", "Imported"), occurred_at=task.created_at)
                    if t.get("status") == "done" and t.get("doneVisitId") in visits:
                        TaskActivity.objects.create(id=stable("completed", sid, t["id"]), task=task, visit=visits[t["doneVisitId"]], action="completed", task_title=t["title"], author_name=t.get("doneBy", "Imported"), occurred_at=stamp(t.get("doneAt")) or task.created_at)
                    ImportRecord.objects.create(source="field-log", source_id=source_id, entity_type="hub.task", entity_id=str(task.pk), payload=t)
                    count += 1
            for c in source.get("comments", []):
                source_id = f"{sid}:comment:{c['id']}"
                if ImportRecord.objects.filter(source="field-log", source_id=source_id).exists():
                    continue
                task = tasks.get(c.get("taskId"))
                visit = visits.get(c.get("visitId"))
                common = {"id": stable("comment", sid, c["id"]), "text": c.get("text", ""), "author_name": c.get("authorName", "Imported"), "occurred_at": stamp(c.get("createdAt")) or datetime.now(timezone.utc)}
                if task:
                    obj = TaskActivity.objects.create(task=task, visit=visit, task_title=task.title, action="commented", **common)
                elif visit:
                    obj = VisitObservation.objects.create(visit=visit, **common)
                else:
                    # Keep orphaned comments in provenance even when no safe parent can be inferred.
                    ImportRecord.objects.create(source="field-log", source_id=source_id, entity_type="orphan-comment", entity_id="", payload=c)
                    continue
                ImportRecord.objects.create(source="field-log", source_id=source_id, entity_type=obj._meta.label_lower, entity_id=str(obj.pk), payload=c)
                count += 1
            for visit in visits.values():
                if visit.status == "closed" and not visit.reports.exists():
                    prefix = "Reconstructed from imported Field Log records; historical task state may be incomplete.\n\n"
                    VisitReport.objects.create(visit=visit, revision=1, text=prefix+render_visit_report(visit), markdown=prefix+render_visit_report(visit, True))
        self.stdout.write(self.style.SUCCESS(f"Imported {count} Field Log records. Reruns do not overwrite edits."))
