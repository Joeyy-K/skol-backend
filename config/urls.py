# config/urls.py (Root URL configuration)
from django.contrib import admin
from django.urls import path, include

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
    path('api/expenses/', include('expenses.urls')),
    path('api/budgets/', include('budgets.urls')),
    path('api/calendar/', include('calendar_events.urls')),
    path('api/', include('subjects.urls')),
    path('api/', include('exams.urls')), 
]