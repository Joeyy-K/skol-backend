# auth_system/urls.py, 
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Authentication views
    RegisterView, LoginView, LogoutView, CurrentUserView,
    
    # Role-based dashboard views
    AdminDashboardView, TeacherDashboardView, StudentDashboardView, ParentDashboardView,
    
    # Management and utility views
    ManagementView, AllUsersListView, ProfileViewSet, ChangePasswordView,
    
    # Test endpoints
    check_user_role, admin_test_endpoint, teacher_test_endpoint
)

app_name = 'auth_system'

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')

urlpatterns = [
    # Authentication endpoints
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    
    # Role-based dashboards
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/teacher/', TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('dashboard/student/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/parent/', ParentDashboardView.as_view(), name='parent_dashboard'),
    
    # Management views
    path('management/', ManagementView.as_view(), name='management'),
    path('users/', AllUsersListView.as_view(), name='all_users'),
    path('settings/password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Utility and test endpoints
    path('check-role/', check_user_role, name='check_role'),
    path('test/admin/', admin_test_endpoint, name='admin_test'),
    path('test/teacher/', teacher_test_endpoint, name='teacher_test'),

    path('', include(router.urls)),
]