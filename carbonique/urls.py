from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hub import api, views
from hub import resources_api as resources
from hub import monitor, processing_files, record_resources

router = DefaultRouter()
for prefix, cls in [("sites", api.SiteViewSet), ("equipment", api.EquipmentViewSet), ("deployments", api.DeploymentViewSet), ("configurations", api.ConfigurationViewSet), ("caveats", api.CaveatViewSet), ("dois", api.DOIViewSet), ("equipment-history", api.HistoryViewSet), ("checklists", api.ChecklistViewSet)]:
    router.register(prefix, cls, basename=prefix)

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("api/bootstrap/", api.bootstrap), path("api/logout/", api.logout), path("api/snapshot/", api.snapshot),
    path("api/processing-files/", processing_files.library),
    path("processing-files/<uuid:pk>/", processing_files.version_file),
    path('api/sites/<int:site_id>/calibrations/', record_resources.calibrations),
    path('api/sites/<int:site_id>/calibrations/<uuid:pk>/', record_resources.calibrations),
    path('api/knowledge/', record_resources.knowledge),
    path('api/knowledge/<uuid:pk>/', record_resources.knowledge),
    path('api/knowledge/<uuid:pk>/files/', record_resources.knowledge_files),
    path('api/knowledge/<uuid:pk>/files/<uuid:file_id>/', record_resources.knowledge_files),
    path('knowledge-files/<uuid:pk>/', record_resources.knowledge_download),
    path("api/monitor/", monitor.tower_status),
    path("api/badm/schema/", resources.badm_schema),
    path("api/sites/<int:site_id>/condition/", resources.condition),
    path("api/sites/<int:site_id>/badm/profile/", resources.profile),
    path("api/sites/<int:site_id>/badm/records/", resources.record),
    path("api/sites/<int:site_id>/badm/records/<uuid:pk>/", resources.record),
    path("sites/<int:site_id>/badm.zip", resources.badm_export),
    path("inventory-source.zip", resources.inventory_source),
    path("api/protocols/", resources.protocols),
    path("api/protocols/<uuid:pk>/", resources.protocols),
    path("protocols/<uuid:pk>/file/", resources.protocol_file),
    path("api/sites/<int:site_id>/media/", resources.media),
    path("api/sites/<int:site_id>/media/<uuid:pk>/", resources.media),
    path("site-media/<uuid:pk>/file/", resources.media_file),
    path("api/sync/", api.sync), path("api/team/", api.team),
    path("api/overview/", api.overview), path("api/csrf/", views.csrf_token),
    path("api/attachments/", api.upload_attachment), path("api/", include(router.urls)),
    path("attachments/<uuid:pk>/", views.attachment_download),
    path("legacy-attachments/<str:kind>/<int:pk>/", views.legacy_download),
    path("export.csv", views.export_csv),
    path("reference/", views.public_reference), path("health/", views.health),
    path("fieldnotes/", views.public_fieldnotes, name="public_fieldnotes"),
    path("fieldnotes/download/", views.fieldnotes_download, name="fieldnotes_download"),
    path("fieldnotes/content/", views.fieldnotes_content, name="fieldnotes_content"),
    path("sw.js", views.service_worker), path("manifest.webmanifest", views.manifest),
]
