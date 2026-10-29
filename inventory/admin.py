from django.contrib import admin
from .models import Site, Equipment, FieldNote, Photo, Document, History, DOI


class ReadOnlyInventoryAdmin(admin.ModelAdmin):
    """Routine edits belong to the scoped, versioned workspace operations."""
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


for model in [Site, Equipment, FieldNote, Photo, Document, History, DOI]:
    admin.site.register(model, ReadOnlyInventoryAdmin)
