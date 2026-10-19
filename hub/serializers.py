import bleach
from rest_framework import serializers
from inventory.models import Site, Equipment, History, DOI
from .models import Visit, Task, TaskActivity, VisitObservation, VisitReport, Deployment, ConfigurationVersion, DataCaveat, Attachment, ChecklistTemplate

HTML_TAGS = {"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "a", "code", "pre", "blockquote", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td"}
def clean_html(text):
    return bleach.clean(text or "", tags=HTML_TAGS, attributes={"a": ["href", "title"]}, protocols=["http", "https", "mailto"], strip=True)

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = "__all__"
        read_only_fields = ["id", "updated_at", "version"]
    def validate_code(self, value):
        value = value.strip().upper()
        qs = Site.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This site code is already in use.")
        return value
    def validate_description(self, value):
        return clean_html(value)
    def validate_metadata(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object.")
        return value

class EquipmentSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=["available", "deployed", "repair", "retired"], required=False)
    class Meta:
        model = Equipment
        fields = "__all__"
        read_only_fields = ["id", "version"]

class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = History
        fields = "__all__"

class DOISerializer(serializers.ModelSerializer):
    class Meta:
        model = DOI
        fields = "__all__"

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"

class VisitSerializer(serializers.ModelSerializer):
    narrative = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()
    class Meta:
        model = Visit
        fields = "__all__"
    def get_narrative(self, obj):
        return clean_html(obj.narrative)
    def get_reports(self, obj):
        return [{"revision": r.revision, "text": r.text, "markdown": r.markdown, "created_at": r.created_at.isoformat()} for r in obj.reports.all()]

class TaskActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskActivity
        fields = "__all__"

class VisitObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitObservation
        fields = "__all__"

class DeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deployment
        fields = "__all__"
        read_only_fields = ["id", "version"]

class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationVersion
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at"]
    def validate_settings(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a JSON object.")
        return value

class CaveatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCaveat
        fields = "__all__"
        read_only_fields = ["id", "created_by", "updated_at", "version"]
    def validate_description(self, value):
        return clean_html(value)
    def validate_treatment(self, value):
        return clean_html(value)

class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = Attachment
        exclude = ["file"]
    def get_url(self, obj):
        return f"/attachments/{obj.id}/"

class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistTemplate
        fields = "__all__"
    def validate_tasks(self, value):
        if not isinstance(value, list) or len(value) > 100:
            raise serializers.ValidationError("Use a list of at most 100 tasks.")
        for task in value:
            if not isinstance(task, dict) or not task.get("title") or len(task["title"]) > 250 or task.get("priority", "normal") not in ("normal", "high"):
                raise serializers.ValidationError("Each task needs a title and a valid priority.")
        return value
