from django.contrib import admin
from .models import Site, Equipment, FieldNote, Photo, Document, History, DOI

class PreserveHistoryAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False
    def get_readonly_fields(self, request, obj=None):
        names = {field.name for field in self.model._meta.fields}
        return tuple(name for name in ("version", "updated_at") if name in names)
    def save_model(self, request, obj, form, change):
        if change and hasattr(obj, "version"):
            obj.version += 1
        super().save_model(request, obj, form, change)

for model in [Site, Equipment, FieldNote, Photo, Document, History, DOI]:
    admin.site.register(model, PreserveHistoryAdmin)
