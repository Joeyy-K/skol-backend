# config/urls.py (Root URL configuration)
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse

from django.db import connection
from auth_system.models import User
from students.models import StudentProfile
from teachers.models import TeacherProfile
from parents.models import ParentProfile
from classes.models import Class
from subjects.models import Subject

def database_health(request):
    """Check if database has been populated with data"""
    try:
        # Count records in each model
        counts = {
            'users': User.objects.count(),
            'students': StudentProfile.objects.count(),
            'teachers': TeacherProfile.objects.count(),
            'parents': ParentProfile.objects.count(),
            'classes': Class.objects.count(),
            'subjects': Subject.objects.count(),
        }
        
        # Check if we have any sample credentials
        sample_credentials = {}
        for role in ['STUDENT', 'TEACHER', 'PARENT']:
            user = User.objects.filter(role=role).first()
            if user:
                sample_credentials[role.lower()] = {
                    'email': user.email,
                    'password': 'password123'  # We know this is the default
                }
        
        return JsonResponse({
            'status': 'healthy',
            'database_populated': any(counts.values()),
            'record_counts': counts,
            'sample_credentials': sample_credentials
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/attendance/', include('attendance.urls')), 
    path('api/auth/', include('auth_system.urls')),
    path('api/students/', include('students.urls')),
    path('api/classes/', include('classes.urls')), 
    path('api/teachers/', include('teachers.urls')), 
    path('api/schedules/', include('schedules.urls')),
    path('api/parents/', include('parents.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/fees/', include('fees.urls')), 
    path('api/', include('subjects.urls')),
    path('api/', include('exams.urls')), 
    path('api/health/', health_check, name='health_check'),
    path('api/db-health/', database_health, name='database_health'),
]