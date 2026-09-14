"""Django settings for the ChatBot QA analysis service."""
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders", "rest_framework", "drf_spectacular", "src.database", "src.api",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "src.core.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "src.core.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": os.getenv("POSTGRES_DB", "chatbot_db"), "USER": os.getenv("POSTGRES_USER", "postgres"), "PASSWORD": os.getenv("POSTGRES_PASSWORD", "pokemega"), "HOST": os.getenv("POSTGRES_HOST", "localhost"), "PORT": os.getenv("POSTGRES_PORT", "5432")}}
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []
LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ = "es-cl", "America/Santiago", True, True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
REST_FRAMEWORK = {"DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"], "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"}
SPECTACULAR_SETTINGS = {"TITLE": "ChatBot QA API", "DESCRIPTION": "API para análisis QA de datos Jira.", "VERSION": "1.0.0"}

# Configuración de Jira
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
# Jira Cloud es la fuente de verdad del chat. La fuente local solo se habilita
# explícitamente con JIRA_DATA_SOURCE=local para pruebas.
JIRA_DATA_SOURCE = os.getenv('JIRA_DATA_SOURCE', 'jira').lower()
AGENT_EXECUTION_MODE = os.getenv('AGENT_EXECUTION_MODE', 'mock').lower()
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY', '')
GITHUB_WORKFLOW_BRANCH = os.getenv('GITHUB_WORKFLOW_BRANCH', 'test')
GITHUB_DISPATCH_TOKEN = os.getenv('GITHUB_DISPATCH_TOKEN', '')
GITHUB_API_TIMEOUT = int(os.getenv('GITHUB_API_TIMEOUT', '15'))

# ================================================================================
# SEGURIDAD - Phase 1: Security Base
# ================================================================================

# Security Headers (HSTS, CSP, X-Frame-Options)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        'default-src': ("'self'",),
        'script-src': ("'self'",),
        'style-src': ("'self'", "'unsafe-inline'"),
        'img-src': ("'self'", "data:", "https:"),
    }

# Session Security
SESSION_COOKIE_SECURE = False  # True en producción (requiere HTTPS)
SESSION_COOKIE_HTTPONLY = True  # Prevenir acceso desde JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expira al cerrar navegador

# CORS Configuration (restrictivo)
CORS_ALLOW_CREDENTIALS = True

# Input Validation
MAX_MESSAGE_LENGTH = 5000
MAX_FILTER_LENGTH = 500