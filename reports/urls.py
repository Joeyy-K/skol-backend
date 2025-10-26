# reports/urls.py
from django.urls import path
from .views import (
    ReportCardDataView, 
    ParentReportCardDataView, 
    ReportPublishingView,
    MyPublishedReportsView,
    PublishedReportDetailView,
    GenerateSingleReportView,
    AdminReportDetailView
)

app_name = 'reports'

urlpatterns = [
    path('student-report-card/', ReportCardDataView.as_view(), name='student-report-card'),
    path('parent-report-card/', ParentReportCardDataView.as_view(), name='parent-report-card'),
    path('publish-reports/', ReportPublishingView.as_view(), name='publish-reports'),
    path('generate-single/', GenerateSingleReportView.as_view(), name='generate-single-report'),
    
    # New parent endpoints
    path('view/admin/<int:pk>/', AdminReportDetailView.as_view(), name='admin-report-detail'),
    path('my-published/', MyPublishedReportsView.as_view(), name='my-published-reports'),
    path('view/<int:pk>/', PublishedReportDetailView.as_view(), name='view-published-report'),
]