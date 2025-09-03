# exams/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExamViewSet, StudentScoreViewSet, TermViewSet, ClassGradebookView

router = DefaultRouter()
router.register(r'exams', ExamViewSet)
router.register(r'scores', StudentScoreViewSet)
router.register(r'terms', TermViewSet)

urlpatterns = [
    path('gradebook/', ClassGradebookView.as_view(), name='class-gradebook'),
    path('', include(router.urls)),
]