# students/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from auth_system.permissions import IsAdminUser, IsTeacherUser
from .models import StudentProfile
from .serializers import StudentProfileSerializer, StudentProfileUpdateSerializer
from .permissions import IsAdminOrTeacher, StudentProfilePermission, IsClassTeacherOrAdmin
from django.db.models import Q 


class StudentProfilePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class StudentProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student profiles with role-based permissions
    """
    queryset = StudentProfile.objects.select_related('user').all()
    serializer_class = StudentProfileSerializer
    lookup_field = 'pk'
    pagination_class = StudentProfilePagination

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsClassTeacherOrAdmin()]
        
        elif self.action in ['create', 'destroy']:
            return [IsAdminUser()]
        
        return [IsAdminOrTeacher()]

    def get_serializer_class(self):
        """
        Use different serializers based on user role and action
        """
        if (self.action in ['update', 'partial_update'] and 
            self.request.user.role == 'STUDENT'):
            return StudentProfileUpdateSerializer
        return StudentProfileSerializer

    def get_queryset(self):
        """
        Filter queryset based on user role
        """
        user = self.request.user
        
        # Start with the base queryset based on user role
        if user.role in ['ADMIN', 'TEACHER']:
            queryset = StudentProfile.objects.select_related('user', 'classroom').all()
        elif user.role == 'STUDENT':
            queryset = StudentProfile.objects.filter(user=user).select_related('user', 'classroom')
        else:
            return StudentProfile.objects.none()
    
        search_query = self.request.query_params.get('search', None)
        if search_query:
            # Use Q objects to search multiple fields with an OR condition
            # `icontains` makes the search case-insensitive
            queryset = queryset.filter(
                Q(user__full_name__icontains=search_query) |
                Q(admission_number__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
            
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """
        List all student profiles (Admin/Teacher only) with pagination
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Student profiles retrieved successfully',
            'count': queryset.count(),
            'results': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific student profile
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'message': 'Student profile retrieved successfully',
            'student': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """
        Create a new student profile (Admin/Teacher only)
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            student_profile = serializer.save()
            return Response({
                'message': 'Student profile created successfully',
                'student': StudentProfileSerializer(student_profile).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update a student profile
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Student profile updated successfully',
                'student': StudentProfileSerializer(instance).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        profile_instance = self.get_object()
        user_instance = profile_instance.user
        user_full_name = user_instance.full_name
        
        user_instance.delete()
        
        return Response(
            {"message": f"Student '{user_full_name}' and their profile have been successfully deleted."},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'])
    def by_class(self, request):
        """
        Get all students belonging to a specific class ID. Not paginated.
        Expects a query parameter: /api/students/profiles/by_class/?class_id=X
        """
        class_id = request.query_params.get('class_id', None)
        if not class_id:
            return Response({'error': 'class_id parameter is required.'}, status=400)

        students = StudentProfile.objects.filter(classroom_id=class_id).select_related('user')
        serializer = self.get_serializer(students, many=True) 
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAdminOrTeacher])
    def academic_info(self, request, pk=None):
        """
        Get academic information for a student (placeholder for future expansion)
        """
        student = self.get_object()
        
        return Response({
            'message': 'Academic information retrieved',
            'student': {
                'id': student.id,
                'admission_number': student.admission_number,
                'full_name': student.user.full_name,
                'class_level': student.class_level,
                'email': student.user.email
            },
            'academic_data': {
                'current_class': student.class_level,
                'enrollment_date': student.created_at,
                'status': 'Active' if student.user.is_active else 'Inactive'
                # Future: Add subjects, grades, attendance, etc.
            }
        })


class MyStudentsView(ListAPIView):
    """
    API view for a Teacher to retrieve a list of students
    from all the classes they are in charge of.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsTeacherUser] # Only teachers can access this
    pagination_class = StudentProfilePagination

    def get_queryset(self):
        """
        Return a queryset of students filtered by the logged-in teacher's
        assigned classes.
        """
        teacher = self.request.user
        
        assigned_class_ids = teacher.classes_in_charge.values_list('id', flat=True)
        
        if not assigned_class_ids:
            return StudentProfile.objects.none()
            
        queryset = StudentProfile.objects.filter(classroom_id__in=assigned_class_ids)
        
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search_query) |
                Q(admission_number__icontains=search_query)
            )
            
        return queryset.select_related('user', 'classroom').order_by('user__full_name')
    
    def list(self, request, *args, **kwargs):
        """
        Override list method to return paginated response in the expected format
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'next': None,
            'previous': None,
            'results': serializer.data
        })