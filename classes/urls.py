from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClassViewSet, MyAssignedClassesView, AllClassesListView

router = DefaultRouter()
router.register(r'', ClassViewSet, basename='class')  

urlpatterns = [
    path('my-classes/', MyAssignedClassesView.as_view(), name='my-assigned-classes'),
    path('all/', AllClassesListView.as_view(), name='all-classes-list'),
    path('', include(router.urls)),
]
