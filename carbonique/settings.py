"""SQLite locally; DATABASE_URL or EcoFlux DB_* in production."""
import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}
DEBUG = env_bool("DEBUG", True)
SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-change-before-deployment-carbonique")
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("development-only")):
    raise ImproperlyConfigured("Set a random SECRET_KEY of at least 50 characters for production.")
ALLOWED_HOSTS = [s.strip() for s in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver").split(",") if s.strip()]
CSRF_TRUSTED_ORIGINS = [s.strip() for s in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if s.strip()]
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "rest_framework", "inventory", "hub", "axes"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "hub.security.SecurityHeadersMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "hub.security.WorkspaceIdentityMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware", "axes.middleware.AxesMiddleware"]
ROOT_URLCONF = "carbonique.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "carbonique.wsgi.application"
ASGI_APPLICATION = "carbonique.asgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3", "OPTIONS": {"timeout": 30}}}
if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60, conn_health_checks=True)
elif os.environ.get("DB_ENGINE"):
    DATABASES["default"] = {"ENGINE": os.environ["DB_ENGINE"], "NAME": os.environ.get("DB_NAME", ""), "USER": os.environ.get("DB_USER", ""), "PASSWORD": os.environ.get("DB_PASSWORD", ""), "HOST": os.environ.get("DB_HOST", ""), "PORT": os.environ.get("DB_PORT", ""), "CONN_MAX_AGE": 60}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "en-ca"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"}}
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT") or BASE_DIR / "media")
MEDIA_URL = "/private-media/"
PHOTO_UPLOAD_SUBDIR = "site_photos"
DOCUMENT_UPLOAD_SUBDIR = "documents"
MEDIA_THUMBNAIL_SUBDIR = "thumbnails"
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
MAX_SITE_MEDIA_BYTES = int(os.environ.get("MAX_SITE_MEDIA_BYTES", 100 * 1024 * 1024))
MONITOR_STATIONS_FILE = os.environ.get("MONITOR_STATIONS_FILE", "")
MONITOR_TIMEOUT = float(os.environ.get("MONITOR_TIMEOUT", 6))
MONITOR_MIN_INTERVAL = int(os.environ.get("MONITOR_MIN_INTERVAL", 30))
MONITOR_STALE_SECONDS = int(os.environ.get("MONITOR_STALE_SECONDS", 300))
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = LOGIN_URL
SESSION_COOKIE_AGE = 12 * 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
if env_bool("TRUST_PROXY_HEADERS"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "carbonique@localhost")
PUBLIC_FIELDNOTES_ENABLED = env_bool("PUBLIC_FIELDNOTES_ENABLED", True)
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"], "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"], "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"], "DEFAULT_PARSER_CLASSES": ["hub.parsers.ObjectJSONParser", "rest_framework.parsers.MultiPartParser", "rest_framework.parsers.FormParser"], "UNAUTHENTICATED_USER": None}

# Persistent login protection shared by all application workers.
AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", "django.contrib.auth.backends.ModelBackend"]
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_CLIENT_IP_CALLABLE = "hub.security.client_ip"
AXES_LOCKOUT_TEMPLATE = "registration/login_locked.html"
AXES_HTTP_RESPONSE_CODE = 429
AXES_DISABLE_ACCESS_LOG = True
AXES_SENSITIVE_PARAMETERS = ["csrfmiddlewaretoken", "token", "secret", "api_key"]
AXES_ALLOWED_CORS_ORIGINS = []
TRUSTED_PROXY_NETWORKS = [item.strip() for item in os.environ.get("TRUSTED_PROXY_NETWORKS", "127.0.0.1/32,::1/128").split(",") if item.strip()]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Set explicit ALLOWED_HOSTS in production; wildcard hosts are not permitted.")
