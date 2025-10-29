from django.db import models
from django.conf import settings

class Event(models.Model):
    """
    A central model to store all time-based events in the school,
    serving as the engine for the system-wide calendar.
    """
    EVENT_TYPE_CHOICES = [
        ('EXAM', 'Exam'),
        ('FEE_DEADLINE', 'Fee Deadline'),
        ('HOLIDAY', 'Holiday'),
        ('SCHOOL_EVENT', 'School Event'),
        ('ACADEMIC_TERM', 'Academic Term'),
        ('CLASS_SCHEDULE', 'Class Schedule'), 
    ]

    group_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Identifier to group recurring events (e.g., 'schedule-123')"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="A concise title for the event (e.g., 'Term 1 Mid-Term Exams')"
    )
    start_time = models.DateTimeField(
        help_text="The start date and time of the event"
    )
    end_time = models.DateTimeField(
        help_text="The end date and time of the event"
    )
    event_type = models.CharField(
        max_length=20, 
        choices=EVENT_TYPE_CHOICES,
        db_index=True # Index for faster filtering by type
    )
    description = models.TextField(
        blank=True,
        help_text="Optional: More details about the event"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_events'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['group_id']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_time.strftime('%Y-%m-%d')})"