# students/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentProfileViewSet, MyStudentsView

app_name = 'students'

student_profile_list = StudentProfileViewSet.as_view({'get': 'list'})

student_by_class = StudentProfileViewSet.as_view({'get': 'by_class'})

router = DefaultRouter()
router.register(r'profiles', StudentProfileViewSet, basename='studentprofile')

urlpatterns = [
    path('profiles/by-class/', student_by_class, name='student-by-class'),
    path('my-students/', MyStudentsView.as_view(), name='my-students'),
    path('', include(router.urls)),
]
