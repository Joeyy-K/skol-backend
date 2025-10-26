from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, HolidayEventView

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
    path('holidays/', HolidayEventView.as_view(), name='holiday-event'),
]