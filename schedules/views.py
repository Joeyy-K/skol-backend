# schedules/views.py
from rest_framework import viewsets, permissions
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from exams.models import Term
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from .models import TimeSlot, ScheduleEntry
from .serializers import TimeSlotSerializer, ScheduleEntrySerializer, ScheduleEntryCreateSerializer
from auth_system.permissions import IsAdminUser


class IsAdminOrReadOnlyForTeachers(permissions.BasePermission):
    """
    Custom permission class:
    - Admins can do anything
    - Teachers have read-only access (list, retrieve)
    - Others have no access
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'ADMIN'):
            return True
        
        if hasattr(request.user, 'role') and request.user.role == 'TEACHER':
            return view.action in ['list', 'retrieve']
        
        return False


class TimeSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing time slots.
    Only admins can create, update, or delete time slots.
    """
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['start_time', 'end_time', 'name']
    ordering = ['start_time']

    def get_permissions(self):
        """
        Assigns permissions based on the action.
        """
        if self.action in ['list', 'retrieve', 'active_slots']:
            return [permissions.IsAuthenticated()]
        
        return [IsAdminUser()]

    @action(detail=False, methods=['get'])
    def active_slots(self, request):
        """
        Custom endpoint to get all active time slots ordered by start time.
        """
        slots = self.get_queryset().order_by('start_time')
        serializer = self.get_serializer(slots, many=True)
        return Response(serializer.data)


class ScheduleEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing schedule entries.
    Admins can do anything, teachers have read-only access.
    Supports filtering by classroom, teacher, and term.
    """
    queryset = ScheduleEntry.objects.all()
    permission_classes = [IsAdminOrReadOnlyForTeachers]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['classroom', 'teacher', 'term', 'day_of_week', 'subject']
    search_fields = ['classroom__name', 'subject__name', 'teacher__full_name']
    ordering_fields = ['day_of_week', 'timeslot__start_time', 'created_at']
    ordering = ['day_of_week', 'timeslot__start_time']

    def get_serializer_class(self):
        """
        Return different serializers based on the action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return ScheduleEntryCreateSerializer
        return ScheduleEntrySerializer

    def get_queryset(self):
        """
        Override to optimize database queries with select_related.
        """
        return ScheduleEntry.objects.select_related(
            'classroom',
            'subject',
            'teacher',
            'timeslot',
            'term'
        ).all()

    @action(detail=False, methods=['get'])
    def by_classroom(self, request):
        """
        Get schedule entries grouped by classroom.
        Requires 'classroom_id' as a query parameter.
        """
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response(
                {'error': 'classroom_id parameter is required'}, 
                status=400
            )
        
        entries = self.get_queryset().filter(classroom_id=classroom_id)
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_teacher(self, request):
        """
        Get schedule entries for a specific teacher.
        Requires 'teacher_id' as a query parameter.
        """
        teacher_id = request.query_params.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id parameter is required'}, 
                status=400
            )
        
        entries = self.get_queryset().filter(teacher_id=teacher_id)
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def weekly_schedule(self, request):
        """
        Get a structured weekly schedule.
        Optionally filter by classroom_id, teacher_id, or term_id.
        """
        queryset = self.get_queryset()
        
        classroom_id = request.query_params.get('classroom_id')
        teacher_id = request.query_params.get('teacher_id')
        term_id = request.query_params.get('term_id')
        
        if classroom_id:
            queryset = queryset.filter(classroom_id=classroom_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        
        schedule_data = {}
        for entry in queryset:
            day = entry.day_of_week
            if day not in schedule_data:
                schedule_data[day] = []
            
            serializer = self.get_serializer(entry)
            schedule_data[day].append(serializer.data)
        
        for day in schedule_data:
            schedule_data[day].sort(key=lambda x: x['timeslot']['start_time'])
        
        return Response(schedule_data)

    @action(detail=False, methods=['get'])
    def teacher_schedule(self, request):
        """
        Get the current user's schedule if they are a teacher.
        """
        if not hasattr(request.user, 'role') or request.user.role != 'TEACHER':
            return Response(
                {'error': 'Only teachers can access this endpoint'}, 
                status=403
            )
        
        entries = self.get_queryset().filter(teacher=request.user)
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)
    
class MyScheduleView(APIView):
    """
    API view to get the personalized weekly schedule for the logged-in user.
    Supports both Teachers and Students.
    """
    
    def get_permissions(self):
        """
        Custom permission method to allow only Teachers and Students.
        """        
        class TeacherOrStudentPermission(BasePermission):
            """
            Custom permission to only allow Teachers and Students to access their schedule.
            """
            def has_permission(self, request, view):
                if not request.user.is_authenticated:
                    return False
                
                if hasattr(request.user, 'role'):
                    return request.user.role in ['TEACHER', 'STUDENT']
                
                return False
        
        return [TeacherOrStudentPermission()]
    
    def get(self, request):
        """
        Get the personalized weekly schedule for the logged-in user.
        """
        try:
            active_term = Term.objects.filter(is_active=True).first()
            if not active_term:
                return Response({
                    'message': 'No active academic term found',
                    'schedule': {}
                }, status=status.HTTP_200_OK)
            
            schedule_entries = ScheduleEntry.objects.none()
            user_info = {}
            
            if request.user.role == 'TEACHER':
                schedule_entries = ScheduleEntry.objects.filter(
                    teacher=request.user,
                    term=active_term
                ).select_related('classroom', 'subject', 'teacher', 'timeslot', 'term')
                
                user_info = {
                    'role': 'TEACHER',
                    'name': request.user.full_name,
                    'context': 'Teaching Schedule'
                }
                
            elif request.user.role == 'STUDENT':
                try:
                    student_profile = request.user.student_profile
                    if student_profile and student_profile.classroom:
                        schedule_entries = ScheduleEntry.objects.filter(
                            classroom=student_profile.classroom,
                            term=active_term
                        ).select_related('classroom', 'subject', 'teacher', 'timeslot', 'term')
                        
                        user_info = {
                            'role': 'STUDENT',
                            'name': request.user.full_name,
                            'classroom': student_profile.classroom.name,
                            'context': 'Class Schedule'
                        }
                    else:
                        user_info = {
                            'role': 'STUDENT',
                            'name': request.user.full_name,
                            'context': 'No Class Assigned'
                        }
                        
                except AttributeError:
                    user_info = {
                        'role': 'STUDENT',
                        'name': request.user.full_name,
                        'context': 'No Student Profile'
                    }
            
            weekly_schedule = {}
            
            for entry in schedule_entries:
                day = entry.day_of_week
                if day not in weekly_schedule:
                    weekly_schedule[day] = []
                
                serializer = ScheduleEntrySerializer(entry)
                weekly_schedule[day].append(serializer.data)
            
            for day in weekly_schedule:
                weekly_schedule[day].sort(key=lambda x: x['timeslot']['start_time'])
            
            response_data = {
                'user_info': user_info,
                'active_term': {
                    'id': active_term.id,
                    'name': active_term.name
                },
                'schedule': weekly_schedule,
                'days_count': len(weekly_schedule),
                'total_entries': sum(len(entries) for entries in weekly_schedule.values())
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'An error occurred while fetching your schedule',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class AllTimeSlotsListView(ListAPIView):
    """
    Provides a simple, non-paginated list of all time slots.
    Required by any authenticated user to build their schedule grid.
    """
    queryset = TimeSlot.objects.all().order_by('start_time')
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated] 
    pagination_class = None 