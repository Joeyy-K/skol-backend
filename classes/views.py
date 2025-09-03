from rest_framework import viewsets, status, filters
from rest_framework.generics import ListAPIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Class
from .serializers import (
    ClassCreateSerializer,
    ClassUpdateSerializer,
    ClassListSerializer,
    ClassDetailSerializer,
    ClassForSelectSerializer
)
from .permissions import IsAdminOrTeacher, IsTeacherInCharge, IsTeacherUser
from auth_system.permissions import IsAdminUser

User = get_user_model()


class ClassViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing school classes with role-based permissions.
    
    Provides CRUD operations for Class model with different serializers
    for different actions and comprehensive filtering/searching capabilities.
    """
    
    queryset = Class.objects.all().select_related('teacher_in_charge').order_by('level', 'name')
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level']
    search_fields = ['name', 'teacher_in_charge__email', 'teacher_in_charge__full_name']
    ordering_fields = ['name', 'level', 'created_at', 'updated_at']
    ordering = ['level', 'name']

    def get_permissions(self):
        """
        Return the appropriate permissions based on the action.
        - Admins can do anything.
        - Teachers can only view the list and details.
        """
        if self.action in ['list', 'retrieve', 'levels', 'teachers', 'unassigned', 'statistics']:
            permission_classes = [IsAdminOrTeacher]
        else:
            permission_classes = [IsAdminUser]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return ClassCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClassUpdateSerializer
        elif self.action == 'list':
            return ClassListSerializer
        elif self.action == 'retrieve':
            return ClassDetailSerializer
        return ClassDetailSerializer
    
    def get_queryset(self):
        """
        Optionally restricts the returned classes based on user role and custom filters.
        """
        queryset = Class.objects.all().select_related('teacher_in_charge')
        
        # Custom filtering based on query parameters
        level = self.request.query_params.get('level', None)
        teacher_id = self.request.query_params.get('teacher_id', None)
        has_teacher = self.request.query_params.get('has_teacher', None)
        
        if level:
            queryset = queryset.filter(level__icontains=level)
        
        if teacher_id:
            queryset = queryset.filter(teacher_in_charge_id=teacher_id)
        
        if has_teacher is not None:
            if has_teacher.lower() in ['true', '1', 'yes']:
                queryset = queryset.filter(teacher_in_charge__isnull=False)
            elif has_teacher.lower() in ['false', '0', 'no']:
                queryset = queryset.filter(teacher_in_charge__isnull=True)
        
        return queryset.order_by('level', 'name')
    
    def create(self, request, *args, **kwargs):
        """
        Create a new class with enhanced response.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform the creation
        instance = serializer.save()
        
        # Return detailed response
        response_serializer = ClassDetailSerializer(instance)
        
        return Response(
            {
                'message': f'Class "{instance.name}" created successfully.',
                'data': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update a class with enhanced response.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Perform the update
        updated_instance = serializer.save()
        
        # Return detailed response
        response_serializer = ClassDetailSerializer(updated_instance)
        
        return Response(
            {
                'message': f'Class "{updated_instance.name}" updated successfully.',
                'data': response_serializer.data
            }
        )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a class.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a class with enhanced response.
        """
        instance = self.get_object()
        class_name = instance.name
        
        # Perform the deletion
        self.perform_destroy(instance)
        
        return Response(
            {
                'message': f'Class "{class_name}" deleted successfully.'
            },
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'])
    def levels(self, request):
        """
        Get all unique class levels.
        """
        levels = Class.objects.values_list('level', flat=True).distinct().order_by('level')
        return Response({
            'levels': list(levels),
            'count': len(levels)
        })
    
    @action(detail=False, methods=['get'])
    def teachers(self, request):
        """
        Get all teachers who can be assigned to classes.
        """
        teachers = User.objects.filter(
            role='TEACHER',
            is_active=True
        ).values('id', 'full_name', 'email').order_by('full_name')

        return Response({
        'teachers': list(teachers), # Convert the QuerySet to a list
        'count': teachers.count()
    })
    
    @action(detail=False, methods=['get'])
    def unassigned(self, request):
        """
        Get all classes without a teacher assigned.
        """
        unassigned_classes = self.get_queryset().filter(teacher_in_charge__isnull=True)
        serializer = ClassListSerializer(unassigned_classes, many=True)
        
        return Response({
            'classes': serializer.data,
            'count': unassigned_classes.count()
        })
    
    @action(detail=True, methods=['post'])
    def assign_teacher(self, request, pk=None):
        """
        Assign a teacher to a specific class.
        """
        class_instance = self.get_object()
        teacher_id = request.data.get('teacher_id')
        
        if not teacher_id:
            return Response(
                {'error': 'teacher_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            teacher = User.objects.get(id=teacher_id, role='TEACHER', is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found or not active.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        class_instance.teacher_in_charge = teacher
        class_instance.save()
        
        serializer = ClassDetailSerializer(class_instance)
        return Response({
            'message': f'Teacher "{teacher.full_name}" assigned to class "{class_instance.name}" successfully.',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def remove_teacher(self, request, pk=None):
        """
        Remove teacher assignment from a specific class.
        """
        class_instance = self.get_object()
        
        if not class_instance.teacher_in_charge:
            return Response(
                {'error': 'No teacher is currently assigned to this class.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        teacher_name = class_instance.teacher_name
        class_instance.teacher_in_charge = None
        class_instance.save()
        
        serializer = ClassDetailSerializer(class_instance)
        return Response({
            'message': f'Teacher "{teacher_name}" removed from class "{class_instance.name}" successfully.',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get class statistics.
        """
        total_classes = self.get_queryset().count()
        assigned_classes = self.get_queryset().filter(teacher_in_charge__isnull=False).count()
        unassigned_classes = total_classes - assigned_classes
        
        level_stats = {}
        for class_obj in self.get_queryset():
            level = class_obj.level
            if level not in level_stats:
                level_stats[level] = {
                    'total': 0,
                    'assigned': 0,
                    'unassigned': 0
                }
            level_stats[level]['total'] += 1
            if class_obj.teacher_in_charge:
                level_stats[level]['assigned'] += 1
            else:
                level_stats[level]['unassigned'] += 1
        
        return Response({
            'total_classes': total_classes,
            'assigned_classes': assigned_classes,
            'unassigned_classes': unassigned_classes,
            'assignment_percentage': round((assigned_classes / total_classes * 100) if total_classes > 0 else 0, 2),
            'level_distribution': level_stats
        })
    
    def perform_create(self, serializer):
        """
        Perform the creation of a new class instance.
        """
        serializer.save()
    
    def perform_update(self, serializer):
        """
        Perform the update of a class instance.
        """
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Perform the deletion of a class instance.
        """
        instance.delete()

class MyAssignedClassesView(ListAPIView):
    """
    API view to retrieve a list of classes specifically assigned to the
    currently logged-in teacher.
    """
    serializer_class = ClassListSerializer
    permission_classes = [IsTeacherUser]    
    def get_queryset(self):
        """
        Overrides the default queryset to return only classes where the 
        'teacher_in_charge' is the user making the request.
        """
        return Class.objects.filter(teacher_in_charge=self.request.user).order_by('name')
    
class AllClassesListView(ListAPIView):
    """
    Provides a simple, non-paginated list of all classes.
    Used for populating dropdown menus throughout the application.
    """
    queryset = Class.objects.all().order_by('name')
    serializer_class = ClassForSelectSerializer
    permission_classes = [IsAdminOrTeacher] # Or whichever roles need this list
    
    pagination_class = None