# schedules/serializers.py
from rest_framework import serializers
from .models import TimeSlot, ScheduleEntry


class TimeSlotSerializer(serializers.ModelSerializer):
    """
    Serializer for TimeSlot model.
    """
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = TimeSlot
        fields = [
            'id',
            'name',
            'start_time',
            'end_time',
            'duration_minutes'
        ]


class ScheduleEntrySerializer(serializers.ModelSerializer):
    """
    Detailed serializer for ScheduleEntry model with nested foreign key information.
    """
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    
    timeslot = TimeSlotSerializer(read_only=True)
        
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    term_name = serializers.CharField(source='term.name', read_only=True)

    class Meta:
        model = ScheduleEntry
        fields = [
            'id',
            'classroom',
            'classroom_name',
            'subject',
            'subject_name',
            'teacher',
            'teacher_name',
            'timeslot',
            'timeslot_id',
            'day_of_week',
            'day_of_week_display',
            'term',
            'term_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_teacher(self, value):
        """
        Validate that the assigned teacher has the correct role.
        """
        if value and hasattr(value, 'role'):
            if value.role != 'TEACHER':
                raise serializers.ValidationError(
                    "Only users with TEACHER role can be assigned to schedule entries."
                )
            if not value.is_active:
                raise serializers.ValidationError(
                    "Only active teachers can be assigned to schedule entries."
                )
        return value

    def validate(self, attrs):
        """
        Object-level validation to check for scheduling conflicts.
        """
        instance = getattr(self, 'instance', None)
        
        classroom = attrs.get('classroom')
        timeslot = attrs.get('timeslot', {}).get('id') if 'timeslot' in attrs else None
        day_of_week = attrs.get('day_of_week')
        term = attrs.get('term')
        
        if instance:
            classroom = classroom or instance.classroom
            timeslot = timeslot or instance.timeslot.id if instance.timeslot else None
            day_of_week = day_of_week or instance.day_of_week
            term = term or instance.term
        
        if classroom and timeslot and day_of_week and term:
            queryset = ScheduleEntry.objects.filter(
                classroom=classroom,
                timeslot_id=timeslot,
                day_of_week=day_of_week,
                term=term
            )
            
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    "A schedule entry already exists for this classroom, timeslot, day, and term combination."
                )
        
        return attrs


class ScheduleEntryCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating schedule entries.
    """
    class Meta:
        model = ScheduleEntry
        fields = [
            'classroom',
            'subject',
            'teacher',
            'timeslot',
            'day_of_week',
            'term'
        ]

    def validate_teacher(self, value):
        """
        Validate that the assigned teacher has the correct role.
        """
        if value and hasattr(value, 'role'):
            if value.role != 'TEACHER':
                raise serializers.ValidationError(
                    "Only users with TEACHER role can be assigned to schedule entries."
                )
            if not value.is_active:
                raise serializers.ValidationError(
                    "Only active teachers can be assigned to schedule entries."
                )
        return value