from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ParentProfileViewSet

router = DefaultRouter()
router.register(r'profiles', ParentProfileViewSet, basename='parentprofile')

urlpatterns = [
    path('', include(router.urls)),
]