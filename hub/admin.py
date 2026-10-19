from django.contrib import admin
from .models import *

class ImmutableAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

class ArchiveOnlyAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    filter_horizontal = ["sites"]

for model in [Visit, Task, TaskActivity, VisitObservation, VisitReport, AuditEvent, OperationReceipt, ImportRecord, ConfigurationVersion, SiteCondition, BADMProfile, BADMRecord, Protocol, SiteMedia, TowerStatus, TowerReading]:
    admin.site.register(model, ImmutableAdmin)
for model in [Deployment, DataCaveat, Attachment, ChecklistTemplate]:
    admin.site.register(model, ArchiveOnlyAdmin)
admin.site.site_header = "Carbonique administration"
admin.site.site_title = "Carbonique Hub"
