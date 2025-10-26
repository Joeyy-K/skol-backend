from rest_framework import viewsets, permissions
from rest_framework.response import Response 
from django.db.models import Q

from fees.models import Invoice 
from .models import Event
from .serializers import EventSerializer
from django.utils.dateparse import parse_datetime
from collections import defaultdict

from rest_framework import viewsets, permissions, status 
from rest_framework.views import APIView 
from auth_system.permissions import IsAdminUser 

from django.utils import timezone 
from datetime import datetime

class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only API endpoint for retrieving calendar events.
    This view now summarizes repetitive events like fee deadlines.
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        Filter events based on date range AND user role.
        """
        queryset = Event.objects.all()
        start_param = self.request.query_params.get('start')
        end_param = self.request.query_params.get('end')

        if start_param:
            start_date = parse_datetime(start_param)
            if start_date:
                queryset = queryset.filter(end_time__gte=start_date)
        if end_param:
            end_date = parse_datetime(end_param)
            if end_date:
                queryset = queryset.filter(start_time__lte=end_date)
        
        user = self.request.user
        
        if not user.is_authenticated:
            return Event.objects.none()

        if user.role == 'ADMIN':
            queryset = queryset.exclude(event_type='CLASS_SCHEDULE')

        elif user.role == 'TEACHER':
            teacher_schedule_ids = [entry.id for entry in user.schedule_entries.all()]
            group_ids = [f"schedule-{id}" for id in teacher_schedule_ids]
            
            queryset = queryset.filter(
                Q(group_id__in=group_ids) | 
                Q(event_type__in=['EXAM', 'HOLIDAY', 'SCHOOL_EVENT'])
            )

        elif user.role == 'STUDENT':
            try:
                student_profile = user.student_profile
                if student_profile.classroom:
                    classroom_schedule_ids = [entry.id for entry in student_profile.classroom.schedule_entries.all()]
                    group_ids = [f"schedule-{id}" for id in classroom_schedule_ids]
                    
                    queryset = queryset.filter(
                        Q(group_id__in=group_ids) | 
                        Q(event_type__in=['EXAM', 'HOLIDAY', 'SCHOOL_EVENT']) 
                    )
                else:
                    queryset = queryset.filter(event_type__in=['HOLIDAY', 'SCHOOL_EVENT'])
            except AttributeError:
                queryset = Event.objects.none() 

        elif user.role == 'PARENT':
            try:
                parent_profile = user.parent_profile
                children_invoices = Invoice.objects.filter(student__in=parent_profile.children.all())
                invoice_ids = [f"invoice-{inv.id}" for inv in children_invoices]
                
                queryset = queryset.filter(
                    Q(group_id__in=invoice_ids) | 
                    Q(event_type__in=['EXAM', 'HOLIDAY', 'SCHOOL_EVENT']) 
                )
            except AttributeError:
                queryset = Event.objects.none() 

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        """
        Override the default list action to implement summarization.
        """
        queryset = self.get_queryset()
        
        events_by_day_and_type = defaultdict(list)
        other_events = []

        for event in queryset:
            if event.event_type == 'FEE_DEADLINE':
                event_date = event.start_time.date()
                events_by_day_and_type[(event_date, event.event_type)].append(event)
            else:
                other_events.append(event)

        summarized_events = []
        for (event_date, event_type), events in events_by_day_and_type.items():
            count = len(events)
            if count > 1:
                first_event = events[0]
                summarized_event_dict = {
                    'id': f'summary-{event_date}-{event_type}',
                    'title': f'{count} Fee Deadlines',
                    'start_time': first_event.start_time,
                    'end_time': first_event.end_time,
                    'event_type': event_type,
                    'description': f'{count} invoices are due on this day. Check the fees module for details.'
                }
                summarized_events.append(summarized_event_dict)
            else:
                other_events.extend(events)

        serialized_other_events = self.get_serializer(other_events, many=True).data
        final_data = serialized_other_events + summarized_events
        
        return Response(final_data)
    
class HolidayEventView(APIView):
    """
    A view for Admins to create, update, or delete Holiday events.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Create a new Holiday event.
        Expects: { "title": "Christmas Break", "start_date": "2025-12-20", "end_date": "2025-12-31" }
        """
        title = request.data.get('title')
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')

        if not all([title, start_date_str, end_date_str]):
            return Response(
                {'error': 'title, start_date, and end_date are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_time = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_time = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        event = Event.objects.create(
            title=title,
            start_time=start_time,
            end_time=end_time,
            event_type='HOLIDAY',
            description=f"School closed for {title}."
        )

        serializer = EventSerializer(event)
        return Response(serializer.data, status=status.HTTP_201_CREATED)