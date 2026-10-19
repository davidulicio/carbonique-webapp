from django.utils.html import strip_tags
from .models import VisitReport, Task

def render_visit_report(visit, markdown=False):
    header = "## " if markdown else ""
    lines = [f"{header}{visit.site.code}: {visit.title or 'Field visit'} · {visit.date}", f"Crew: {visit.crew or 'Not recorded'}", f"Visit type: {visit.get_classification_display()}"]
    def section(title):
        lines.extend(["", ("### " if markdown else "") + title])
    if visit.narrative:
        section("Field notes")
        lines.append(strip_tags(visit.narrative))
    activities = list(visit.task_activities.order_by("occurred_at", "recorded_at"))
    for action, label in [("completed", "Work completed"), ("reopened", "Tasks reopened"), ("created", "New tasks"), ("commented", "Task observations"), ("edited", "Task changes")]:
        events = [a for a in activities if a.action == action]
        if events:
            section(label)
            for a in events:
                lines.append(f"- {a.task_title} ({a.author_name})" + (f": {a.text}" if a.text else ""))
    observations = list(visit.observations.all())
    if observations:
        section("Visit observations")
        lines.extend(f"- {o.author_name}: {o.text}" for o in observations)
    section("Open tasks when this report was generated")
    pending = Task.objects.filter(site=visit.site, status="pending").order_by("priority", "created_at")
    lines.extend([f"- {t.title}" for t in pending] or ["- None"])
    return "\n".join(lines) + "\n"

def close_report(visit, user):
    revision = (visit.reports.order_by("-revision").values_list("revision", flat=True).first() or 0) + 1
    return VisitReport.objects.create(visit=visit, revision=revision, text=render_visit_report(visit), markdown=render_visit_report(visit, True), created_by=user)
