from decouple import config, Csv
from pathlib import Path
import dj_database_url  # 1. Import dj_database_url
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# 2. Update DEBUG setting
# On Render, you will set DEBUG to False. Locally, it's True in your .env file.
DEBUG = config('DEBUG', default=False, cast=bool)

# Allow default hosts if not set
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,.onrender.com,skol-backend-zvs3.onrender.com",
    cast=Csv()
)

# Safety fallback in case env parsing fails
if ".onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".onrender.com")
if "skol-backend-zvs3.onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("skol-backend-zvs3.onrender.com")

# Application definition
INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd-party
    'rest_framework',
    'rest_framework_simplejwt',  # Added JWT support
    'rest_framework_simplejwt.token_blacklist',  # Added for logout blacklisting
    'corsheaders',
    'djoser',
    'django_filters',

    # Custom apps
    'auth_system.apps.AuthSystemConfig', 
    'attendance.apps.AttendanceConfig',
    'students.apps.StudentsConfig', 
    'teachers.apps.TeachersConfig', 
    'schedules.apps.SchedulesConfig',
    'parents.apps.ParentsConfig',
    'reports.apps.ReportsConfig',
    'classes.apps.ClassesConfig',
    'fees.apps.FeesConfig',
    'subjects',
    'exams',
]

# 3. Update MIDDLEWARE for WhiteNoise
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Updated REST Framework Configuration for JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Changed to JWT
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10  
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),  # Short-lived access tokens
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # Standard refresh tokens (not remembered)
    'REFRESH_TOKEN_LIFETIME_REMEMBERED': timedelta(days=30),  # Long-lived for "Remember Me"
    'ROTATE_REFRESH_TOKENS': True,                   # Generate new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,               # Blacklist old refresh tokens
    'UPDATE_LAST_LOGIN': True,                       # Update user's last_login on token generation
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JTI_CLAIM': 'jti',
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=15),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# 4. Update DATABASE configuration
# Replace your existing DATABASES dictionary with this logic.
DATABASES = {
    'default': dj_database_url.config(
        # This will use the DATABASE_URL from your .env file in development,
        # and the one provided by Render in production.
        default=f'sqlite:///{BASE_DIR}/db.sqlite3',
        conn_max_age=600
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# 5. Update STATIC FILES configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # This is where 'collectstatic' will put files

# Add STATICFILES_DIRS to tell Django where to find your apps' static files
STATICFILES_DIRS = [
    BASE_DIR / "static",  # A project-level static folder if you have one
]

# Configure WhiteNoise to handle static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

AUTH_USER_MODEL = 'auth_system.User'