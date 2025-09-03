from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TimeSlotViewSet, ScheduleEntryViewSet, MyScheduleView, AllTimeSlotsListView

router = DefaultRouter()
router.register(r'timeslots', TimeSlotViewSet, basename='timeslot')
router.register(r'schedule-entries', ScheduleEntryViewSet, basename='scheduleentry')

urlpatterns = [
    path('all-timeslots/', AllTimeSlotsListView.as_view(), name='all-timeslots-list'),
    path('my-schedule/', MyScheduleView.as_view(), name='my-schedule'),
    path('', include(router.urls)),
]
