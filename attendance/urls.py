from django.urls import path
from .views import AttendanceViewSet, PersonalAttendanceView 

attendance_sheet_view = AttendanceViewSet.as_view({'get': 'sheet', 'post': 'sheet'})

urlpatterns = [
    path('sheet/', attendance_sheet_view, name='attendance-sheet'),
    path('my-view/', PersonalAttendanceView.as_view(), name='personal-attendance-view'),
]