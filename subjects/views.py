from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from collections import defaultdict

from .models import Subject
from .serializers import (
    SubjectCreateSerializer,
    SubjectUpdateSerializer,
    SubjectListSerializer,
    SubjectDetailSerializer,
    SubjectAssignmentSerializer,
    SubjectStatisticsSerializer,
    SubjectBulkCreateSerializer,
)
from .permissions import IsAdminOrTeacher, IsTeacherInCharge, IsAdminUser 
from auth_system.permissions import IsAdminUser

User = get_user_model()


class SubjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing school subjects with role-based permissions.
    
    Provides CRUD operations for Subject model with different serializers
    for different actions and comprehensive filtering/searching capabilities.
    """
    
    queryset = Subject.objects.all().select_related('teacher_in_charge').order_by('level', 'name')
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'teacher_in_charge']
    search_fields = ['name', 'code', 'teacher_in_charge__email', 'teacher_in_charge__first_name', 'teacher_in_charge__last_name']
    ordering_fields = ['name', 'code', 'level', 'created_at', 'updated_at']
    ordering = ['level', 'name']

    def get_permissions(self):
        """
        Return the appropriate permissions based on the action.
        - Admins can do anything.
        - Teachers can only view the list and details.
        """
        if self.action in ['list', 'retrieve', 'statistics', 'levels']:
            permission_classes = [IsAdminOrTeacher]
        else:
            permission_classes = [IsAdminUser]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return SubjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SubjectUpdateSerializer
        elif self.action == 'list':
            return SubjectListSerializer
        elif self.action == 'retrieve':
            return SubjectDetailSerializer
        elif self.action == 'assign_teacher':
            return SubjectAssignmentSerializer
        elif self.action == 'statistics':
            return SubjectStatisticsSerializer
        elif self.action == 'bulk_create':
            return SubjectBulkCreateSerializer
        return SubjectDetailSerializer
    
    def get_permissions(self):
        """
        Return the appropriate permissions based on the action.
        Admins can do anything. Teachers can view.
        """
        if self.action in ['create', 'bulk_create', 'update', 'partial_update', 'destroy', 'assign_teacher', 'remove_teacher']:
            permission_classes = [IsAdminUser] 
        else: 
            permission_classes = [IsAdminOrTeacher] 
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Optionally restricts the returned subjects based on user role and custom filters.
        """
        queryset = Subject.objects.all().select_related('teacher_in_charge')
        
        level = self.request.query_params.get('level', None)
        teacher_id = self.request.query_params.get('teacher_id', None)
        has_teacher = self.request.query_params.get('has_teacher', None)
        code = self.request.query_params.get('code', None)
        
        if level:
            queryset = queryset.filter(level__icontains=level)
        
        if teacher_id:
            queryset = queryset.filter(teacher_in_charge_id=teacher_id)
        
        if has_teacher is not None:
            if has_teacher.lower() in ['true', '1', 'yes']:
                queryset = queryset.filter(teacher_in_charge__isnull=False)
            elif has_teacher.lower() in ['false', '0', 'no']:
                queryset = queryset.filter(teacher_in_charge__isnull=True)
        
        if code:
            queryset = queryset.filter(code__icontains=code)
        
        return queryset.order_by('level', 'name')
    
    def create(self, request, *args, **kwargs):
        """
        Create a new subject with enhanced response.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        instance = serializer.save()
        
        response_serializer = SubjectDetailSerializer(instance)
        
        return Response(
            {
                'message': f'Subject "{instance.name}" ({instance.code}) created successfully.',
                'data': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update a subject with enhanced response.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        updated_instance = serializer.save()
        
        response_serializer = SubjectDetailSerializer(updated_instance)
        
        return Response(
            {
                'message': f'Subject "{updated_instance.name}" ({updated_instance.code}) updated successfully.',
                'data': response_serializer.data
            }
        )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a subject.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a subject with enhanced response.
        """
        instance = self.get_object()
        subject_name = instance.name
        subject_code = instance.code
        
        self.perform_destroy(instance)
        
        return Response(
            {
                'message': f'Subject "{subject_name}" ({subject_code}) deleted successfully.'
            },
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrTeacher])
    def assign_teacher(self, request, pk=None):
        """
        Assign a teacher to a specific subject.
        
        POST /subjects/<pk>/assign_teacher/
        Body: {"teacher_id": <id>}
        """
        subject_instance = self.get_object()
        serializer = SubjectAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        teacher_id = serializer.validated_data['teacher_id']
        
        try:
            teacher = User.objects.get(id=teacher_id, role='TEACHER', is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found or not active.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if subject_instance.teacher_in_charge == teacher:
            return Response(
                {'error': f'Teacher "{teacher.full_name or teacher.email} is already assigned to this subject.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subject_instance.teacher_in_charge = teacher
        subject_instance.save()
        
        response_serializer = SubjectDetailSerializer(subject_instance)
        return Response({
            'message': f'Teacher "{teacher.full_name or teacher.email}" assigned to subject "{subject_instance.name}" ({subject_instance.code}) successfully.',
            'data': response_serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrTeacher])
    def remove_teacher(self, request, pk=None):
        """
        Remove teacher assignment from a specific subject.
        
        POST /subjects/<pk>/remove_teacher/
        """
        subject_instance = self.get_object()
        
        if not subject_instance.teacher_in_charge:
            return Response(
                {'error': 'No teacher is currently assigned to this subject.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        teacher_name = subject_instance.teacher_name
        subject_instance.teacher_in_charge = None
        subject_instance.save()
        
        response_serializer = SubjectDetailSerializer(subject_instance)
        return Response({
            'message': f'Teacher "{teacher_name}" removed from subject "{subject_instance.name}" ({subject_instance.code}) successfully.',
            'data': response_serializer.data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrTeacher])
    def statistics(self, request):
        """
        Get subject statistics.
        
        GET /subjects/statistics/
        """
        queryset = self.get_queryset()
        total_subjects = queryset.count()
        assigned_subjects = queryset.filter(teacher_in_charge__isnull=False).count()
        unassigned_subjects = total_subjects - assigned_subjects
        
        assignment_percentage = round(
            (assigned_subjects / total_subjects * 100) if total_subjects > 0 else 0, 2
        )
        
        level_stats = defaultdict(int)
        for subject in queryset:
            level_stats[subject.level] += 1
        level_distribution = dict(level_stats)
        
        subjects_by_teacher = defaultdict(int)
        for subject in queryset.filter(teacher_in_charge__isnull=False):
            teacher_name = subject.teacher_in_charge.full_name or subject.teacher_in_charge.email
            subjects_by_teacher[teacher_name] += 1
        subjects_by_teacher = dict(subjects_by_teacher)
        
        statistics_data = {
            'total_subjects': total_subjects,
            'assigned_subjects': assigned_subjects,
            'unassigned_subjects': unassigned_subjects,
            'assignment_percentage': assignment_percentage,
            'level_distribution': level_distribution,
            'subjects_by_teacher': subjects_by_teacher
        }
        
        serializer = SubjectStatisticsSerializer(statistics_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrTeacher])
    def bulk_create(self, request):
        """
        Create multiple subjects at once.
        
        POST /subjects/bulk_create/
        Body: {"subjects": [{"name": "...", "code": "...", ...}, ...]}
        """
        serializer = SubjectBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            subjects_data = serializer.validated_data['subjects']
            created_subjects = []
            failed_subjects = []
            
            for subject_data in subjects_data:
                try:
                    subject = Subject.objects.create(**subject_data)
                    created_subjects.append(subject)
                except Exception as e:
                    failed_subjects.append({
                        'data': subject_data,
                        'error': str(e)
                    })
            
            created_serializer = SubjectDetailSerializer(created_subjects, many=True)
            
            response_data = {
                'message': f'Bulk creation completed. {len(created_subjects)} subjects created successfully.',
                'created_count': len(created_subjects),
                'failed_count': len(failed_subjects),
                'created_subjects': created_serializer.data
            }
            
            if failed_subjects:
                response_data['failed_subjects'] = failed_subjects
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Bulk creation failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def levels(self, request):
        """
        Get all unique subject levels.
        """
        levels = Subject.objects.values_list('level', flat=True).distinct().order_by('level')
        return Response({
            'levels': list(levels),
            'count': len(levels)
        })
    
    @action(detail=False, methods=['get'])
    def teachers(self, request):
        """
        Get all teachers who can be assigned to subjects.
        """
        teachers = User.objects.filter(
            role='TEACHER',
            is_active=True
        ).values('id', 'first_name', 'last_name', 'email').order_by('first_name', 'last_name')
        
        teachers_list = []
        for teacher in teachers:
            teacher['full_name'] = f"{teacher['first_name']} {teacher['last_name']}".strip()
            teachers_list.append(teacher)
        
        return Response({
            'teachers': teachers_list,
            'count': len(teachers_list)
        })
    
    @action(detail=False, methods=['get'])
    def unassigned(self, request):
        """
        Get all subjects without a teacher assigned.
        """
        unassigned_subjects = self.get_queryset().filter(teacher_in_charge__isnull=True)
        serializer = SubjectListSerializer(unassigned_subjects, many=True)
        
        return Response({
            'subjects': serializer.data,
            'count': unassigned_subjects.count()
        })
    
    def perform_create(self, serializer):
        """
        Perform the creation of a new subject instance.
        """
        serializer.save()
    
    def perform_update(self, serializer):
        """
        Perform the update of a subject instance.
        """
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Perform the deletion of a subject instance.
        """
        instance.delete()