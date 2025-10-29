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
from threading import Timer
import requests

def start_keep_alive():
    """Start the keep-alive mechanism"""
    def ping_self():
        try:
            requests.get("https://skol-backend-zvs3.onrender.com/api/health/", timeout=10)
            # Schedule next ping in 10 minutes (600 seconds)
            Timer(600, ping_self).start()
        except:
            pass  # Ignore failures
    
    # Start the ping cycle
    Timer(600, ping_self).start()

def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
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
]