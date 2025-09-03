from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherProfileViewSet, AllTeachersListView

router = DefaultRouter()
router.register(r'profiles', TeacherProfileViewSet, basename='teacherprofile')

urlpatterns = [
    path('all/', AllTeachersListView.as_view(), name='all-teachers-list'),
    path('', include(router.urls)),
]