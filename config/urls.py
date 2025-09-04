# config/urls.py (Root URL configuration)
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse


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
]