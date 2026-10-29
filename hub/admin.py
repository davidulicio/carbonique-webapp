from django.contrib import admin
from .models import *

class ImmutableAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    filter_horizontal = ["sites"]
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission

for model in [Visit, Task, TaskActivity, VisitObservation, VisitReport, AuditEvent, OperationReceipt, ImportRecord, ConfigurationVersion, SiteCondition, BADMProfile, BADMRecord, Protocol, SiteMedia, TowerStatus, TowerReading, ProcessingFile, ProcessingFileVersion]:
    admin.site.register(model, ImmutableAdmin)
for model in [Deployment, DataCaveat, Attachment, ChecklistTemplate]:
    admin.site.register(model, ImmutableAdmin)
admin.site.site_header = "Carbonique administration"
admin.site.site_title = "Carbonique Hub"

from .models import CalibrationLog, KnowledgeEntry, KnowledgeFile
admin.site.register(CalibrationLog, ImmutableAdmin)
admin.site.register(KnowledgeEntry, ImmutableAdmin)
admin.site.register(KnowledgeFile, ImmutableAdmin)
