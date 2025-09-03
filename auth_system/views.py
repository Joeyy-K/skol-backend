from rest_framework import status, permissions, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.decorators import action
from django.db.models import Count
from django.conf import settings
from datetime import timedelta

# JWT imports
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from attendance.serializers import AttendanceRecordSerializer
from parents.models import ParentProfile
from .serializers import (
    ParentDashboardChildSerializer,
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    DashboardScoreSerializer,
    DashboardClassSerializer,
    DashboardSubjectSerializer,
    DashboardExamSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer
)
from students.models import StudentProfile
from exams.models import StudentScore
from .models import User
from classes.models import Class
from subjects.models import Subject
from exams.models import Exam
from .permissions import (
    IsAdminUser, 
    IsTeacherUser, 
    IsStudentUser, 
    IsParentUser,
    IsAdminOrTeacher,
    IsAdminOrOwner
)


# ==========================================
# JWT AUTHENTICATION VIEWS
# ==========================================

class RegisterView(APIView):
    """
    User registration endpoint with auto-login using JWT
    Returns JWT tokens for automatic login
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
class CustomRefreshToken(RefreshToken):
    """Custom refresh token that supports remember me functionality"""
    
    @classmethod
    def for_user_with_remember_me(cls, user, remember_me=False):
        """
        Create a refresh token for a user with optional extended expiration
        """
        token = cls.for_user(user)
        
        if remember_me:
            remember_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get(
                'REFRESH_TOKEN_LIFETIME_REMEMBERED', 
                timedelta(days=30)
            )
            token.set_exp(lifetime=remember_lifetime)
            token['remember_me'] = True
            
        return token


class LoginView(APIView):
    """User login endpoint with JWT token generation and Remember Me support"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            remember_me = request.data.get('remember_me', False)
            
            refresh = CustomRefreshToken.for_user_with_remember_me(user, remember_me)
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'remember_me': remember_me  
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    User logout endpoint with JWT token blacklisting
    Accepts refresh token in request body and blacklists it
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                return Response({
                    'success': True,
                    'message': 'Logout successful - token blacklisted'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': True,
                    'message': 'Logout successful - clear tokens on client'
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error during logout: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(APIView):
    """Get current user information - Any authenticated user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'user': serializer.data
        }, status=status.HTTP_200_OK)


# ==========================================
# ROLE-BASED DEMO VIEWS (unchanged)
# ==========================================

class AdminDashboardView(APIView):
    """
    Admin-only dashboard with system statistics
    Demonstrates IsAdminUser permission
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        user_stats = User.objects.values('role').annotate(count=Count('role'))
        
        stats_dict = {stat['role']: stat['count'] for stat in user_stats}
        
        total_classes = Class.objects.count()
        total_subjects = Subject.objects.count()
        total_exams = Exam.objects.count()
        
        return Response({
            'message': 'Welcome to Admin Dashboard',
            'admin_user': {
                'id': request.user.id,
                'email': request.user.email,
                'full_name': request.user.full_name
            },
            'system_stats': {
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(is_active=True).count(),
                'users_by_role': stats_dict,
                'recent_registrations': User.objects.count(),
                'total_classes': total_classes,
                'total_subjects': total_subjects,
                'total_exams': total_exams,
            }
        }, status=status.HTTP_200_OK)


class AllUsersListView(ListAPIView):
    """
    List all users - Admin only
    Demonstrates using permissions with generic views
    """
    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by('-date_joined')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'message': 'All users retrieved successfully',
            'total_count': self.get_queryset().count(),
            'users': response.data
        })


class TeacherDashboardView(APIView):
    """
    Teacher-only dashboard with dynamic data about their responsibilities.
    """
    permission_classes = [IsTeacherUser]

    def get(self, request):
        teacher = request.user

        assigned_classes = Class.objects.filter(teacher_in_charge=teacher)
        
        assigned_subjects = Subject.objects.filter(teacher_in_charge=teacher)
        
        recent_exams = Exam.objects.filter(created_by=teacher).order_by('-date')[:5]

        classes_serializer = DashboardClassSerializer(assigned_classes, many=True)
        subjects_serializer = DashboardSubjectSerializer(assigned_subjects, many=True)
        exams_serializer = DashboardExamSerializer(recent_exams, many=True)

        dashboard_data = {
            'assigned_classes': classes_serializer.data,
            'assigned_subjects': subjects_serializer.data,
            'recent_exams': exams_serializer.data,
            'class_count': assigned_classes.count(),
            'subject_count': assigned_subjects.count(),
        }

        return Response({
            'message': f"Welcome to your dashboard, {teacher.full_name}!",
            'dashboard_data': dashboard_data
        }, status=status.HTTP_200_OK)


class StudentDashboardView(APIView):
    """
    Student-only dashboard with dynamic data about their class and performance.
    """
    permission_classes = [IsStudentUser] 

    def get(self, request):
        student_user = request.user

        dashboard_data = {
            'classroom_info': None,
            'recent_scores': []
        }

        try:
            profile = StudentProfile.objects.select_related('classroom', 'classroom__teacher_in_charge').get(user=student_user)
            if profile.classroom:
                dashboard_data['classroom_info'] = {
                    'name': profile.classroom.name,
                    'level': profile.classroom.level,
                    'teacher_in_charge': profile.classroom.teacher_in_charge.full_name if profile.classroom.teacher_in_charge else 'N/A'
                }

            recent_scores = StudentScore.objects.filter(
                student=profile
            ).select_related('exam', 'exam__subject').order_by('-exam__date')[:10]
            
            scores_serializer = DashboardScoreSerializer(recent_scores, many=True)
            dashboard_data['recent_scores'] = scores_serializer.data

        except StudentProfile.DoesNotExist:
            pass

        return Response({
            'message': f"Welcome to your portal, {student_user.full_name}!",
            'dashboard_data': dashboard_data
        }, status=status.HTTP_200_OK)

class ParentDashboardView(APIView):
    """
    Parent-only dashboard with dynamic data about linked children.
    Simplified approach using direct ParentProfile access.
    """
    permission_classes = [IsParentUser]

    def get(self, request):
        parent_user = request.user
        
        children_data = []
        try:
            parent_profile = ParentProfile.objects.get(user=parent_user)
            
            linked_children = parent_profile.children.all()
            
            for child_profile in linked_children:
                child_serializer = ParentDashboardChildSerializer(child_profile)
                data_for_this_child = child_serializer.data
                
                recent_scores = child_profile.exam_scores.select_related(
                    'exam', 'exam__subject'
                ).order_by('-exam__date')[:10]
                
                scores_serializer = DashboardScoreSerializer(recent_scores, many=True)
                data_for_this_child['recent_scores'] = scores_serializer.data
                
                serialized_scores = data_for_this_child['recent_scores']
                if serialized_scores:
                    valid_percentages = [
                        float(s['percentage']) for s in serialized_scores if s.get('percentage') is not None
                    ]
                    avg_percentage = sum(valid_percentages) / len(valid_percentages) if valid_percentages else 0
                    
                    academic_summary = {
                        'total_assessments': len(serialized_scores),
                        'average_percentage': round(avg_percentage, 1),
                        'subjects_count': len(set(s['subject_name'] for s in serialized_scores))
                    }
                else:
                    academic_summary = {
                        'total_assessments': 0,
                        'average_percentage': 0,
                        'subjects_count': 0
                    }
                
                data_for_this_child['academic_summary'] = academic_summary
                
                children_data.append(data_for_this_child)
            
        except ParentProfile.DoesNotExist:
            pass
        except Exception as e:
            print(f"Error in ParentDashboardView: {e}")

        return Response({
            'message': f"Welcome to the Parent Portal, {request.user.full_name}!",
            'dashboard_data': {
                'children': children_data
            }
        }, status=status.HTTP_200_OK)
    
class ManagementView(APIView):
    """
    Admin or Teacher access - Demonstrates composite permissions
    Uses IsAdminOrTeacher permission
    """
    permission_classes = [IsAdminOrTeacher]

    def get(self, request):
        user_role = request.user.role
        
        if user_role == 'ADMIN':
            message = 'Admin accessing management features'
            features = [
                'User Management',
                'System Settings',
                'Reports & Analytics',
                'School Configuration'
            ]
        else:  # TEACHER
            message = 'Teacher accessing management features'
            features = [
                'Class Management',
                'Student Reports',
                'Assignment Tools',
                'Grade Book'
            ]

        return Response({
            'message': message,
            'user_role': user_role,
            'available_features': features
        }, status=status.HTTP_200_OK)


class ProfileViewSet(viewsets.GenericViewSet,
                   viewsets.mixins.RetrieveModelMixin,
                   viewsets.mixins.UpdateModelMixin):
    """
    Manages user profiles.
    - Admins can retrieve/update any profile via /api/auth/profiles/{id}/
    - Authenticated users can retrieve/update their own profile via /api/auth/profiles/me/
    """
    queryset = User.objects.all()
    
    def get_serializer_class(self):
        # Use a more secure serializer for updates
        if self.action in ['update', 'partial_update', 'me_update']:
             return UpdateProfileSerializer
        return UserSerializer

    def get_permissions(self):
        # Admins can do anything. Users can only access the 'me' endpoint or their own object.
        if self.action in ['retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsAdminOrOwner()]
        elif self.action in ['me', 'me_update']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()] # Default to admin for any other actions

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def me(self, request, *args, **kwargs):
        """
        Custom action for the logged-in user to view and update their own profile.
        """
        self.kwargs['pk'] = request.user.pk 
        if request.method == 'GET':
            return self.retrieve(request, *args, **kwargs)
        elif request.method in ['PUT', 'PATCH']:
            return self.update(request, *args, **kwargs)

class ChangePasswordView(generics.GenericAPIView):
    """
    Change user password - Authenticated users only
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        """Handle password change request"""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# UTILITY VIEWS FOR TESTING PERMISSIONS
# ==========================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_user_role(request):
    """
    Utility endpoint to check current user's role
    Useful for frontend development and testing
    """
    return Response({
        'user_id': request.user.id,
        'email': request.user.email,
        'role': request.user.role,
        'is_active': request.user.is_active,
        'permissions': {
            'is_admin': request.user.role == 'ADMIN',
            'is_teacher': request.user.role == 'TEACHER',
            'is_student': request.user.role == 'STUDENT',
            'is_parent': request.user.role == 'PARENT',
            'is_management': request.user.role in ['ADMIN', 'TEACHER']
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_test_endpoint(request):
    """Simple admin-only test endpoint"""
    return Response({
        'message': 'SUCCESS! You have admin access.',
        'admin_email': request.user.email
    })


@api_view(['GET'])
@permission_classes([IsTeacherUser])
def teacher_test_endpoint(request):
    """Simple teacher-only test endpoint"""
    return Response({
        'message': 'SUCCESS! You have teacher access.',
        'teacher_email': request.user.email
    })