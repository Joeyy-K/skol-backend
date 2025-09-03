# schedules/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class TimeSlot(models.Model):
    """
    Model representing a single period in the school day.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Time slot identifier, e.g., 'Period 1', 'Break Time'"
    )
    start_time = models.TimeField(
        help_text="Start time of the period"
    )
    end_time = models.TimeField(
        help_text="End time of the period"
    )

    class Meta:
        ordering = ['start_time']
        verbose_name = "Time Slot"
        verbose_name_plural = "Time Slots"

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"

    def clean(self):
        """
        Custom validation to ensure end_time is after start_time.
        """
        super().clean()
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time.'
                })

    def save(self, *args, **kwargs):
        """
        Override save method to call clean() for validation.
        """
        self.clean()
        super().save(*args, **kwargs)

    @property
    def duration_minutes(self):
        """
        Returns the duration of the time slot in minutes.
        """
        if self.start_time and self.end_time:
            start_datetime = timezone.datetime.combine(timezone.datetime.today(), self.start_time)
            end_datetime = timezone.datetime.combine(timezone.datetime.today(), self.end_time)
            duration = end_datetime - start_datetime
            return int(duration.total_seconds() / 60)
        return 0


class ScheduleEntry(models.Model):
    """
    Model representing a single class session in the timetable.
    """
    DAY_CHOICES = [
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ]

    classroom = models.ForeignKey(
        'classes.Class',
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        help_text="The class/classroom for this schedule entry"
    )
    subject = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        help_text="The subject being taught"
    )
    teacher = models.ForeignKey(
        'auth_system.User',
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        limit_choices_to={'role': 'TEACHER', 'is_active': True},
        help_text="Teacher assigned to teach this session"
    )
    timeslot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        help_text="Time slot for this class session"
    )
    day_of_week = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        help_text="Day of the week for this class session"
    )
    term = models.ForeignKey(
        'exams.Term',
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        help_text="Academic term for this schedule entry"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Schedule Entry"
        verbose_name_plural = "Schedule Entries"
        ordering = ['day_of_week', 'timeslot__start_time']
        
        constraints = [
            models.UniqueConstraint(
                fields=['term', 'classroom', 'timeslot', 'day_of_week'],
                name='unique_classroom_timeslot_per_term_day'
            )
        ]
        
        indexes = [
            models.Index(fields=['classroom', 'term']),
            models.Index(fields=['teacher', 'term']),
            models.Index(fields=['day_of_week', 'timeslot']),
        ]

    def __str__(self):
        return f"{self.classroom.name} - {self.subject.name} - {self.get_day_of_week_display()} {self.timeslot.name}"

    def clean(self):
        """
        Custom validation for schedule entries.
        """
        super().clean()
        
        if self.teacher and hasattr(self.teacher, 'role'):
            if self.teacher.role != 'TEACHER':
                raise ValidationError({
                    'teacher': 'Only users with TEACHER role can be assigned to schedule entries.'
                })
            if not self.teacher.is_active:
                raise ValidationError({
                    'teacher': 'Only active teachers can be assigned to schedule entries.'
                })

    def save(self, *args, **kwargs):
        """
        Override save method to call clean() for validation.
        """
        self.clean()
        super().save(*args, **kwargs)

    @property
    def teacher_name(self):
        """
        Returns the full name of the assigned teacher.
        """
        return self.teacher.full_name if self.teacher else "No teacher assigned"

    @property
    def classroom_name(self):
        """
        Returns the name of the classroom.
        """
        return self.classroom.name if self.classroom else "No classroom assigned"

    @property
    def subject_name(self):
        """
        Returns the name of the subject.
        """
        return self.subject.name if self.subject else "No subject assigned"