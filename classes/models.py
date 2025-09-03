from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class Class(models.Model):
    """
    Model representing a school class/grade section.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Class name, e.g., 'Grade 4 West'"
    )
    level = models.CharField(
        max_length=50,
        help_text="Class level, e.g., 'Grade 4'"
    )
    teacher_in_charge = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_in_charge',
        limit_choices_to={'role': 'TEACHER'},
        help_text="Teacher responsible for this class"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        ordering = ['level', 'name']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['teacher_in_charge']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """
        Custom validation to ensure teacher_in_charge has TEACHER role.
        """
        super().clean()
        
        if self.teacher_in_charge:
            if not hasattr(self.teacher_in_charge, 'role'):
                raise ValidationError({
                    'teacher_in_charge': 'User must have a role field.'
                })
            
            if self.teacher_in_charge.role != 'TEACHER':
                raise ValidationError({
                    'teacher_in_charge': 'Only users with TEACHER role can be assigned as teacher in charge.'
                })
            
            # Check if teacher is active
            if not self.teacher_in_charge.is_active:
                raise ValidationError({
                    'teacher_in_charge': 'Teacher must be an active user.'
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
        Returns the full name of the teacher in charge.
        """
        if self.teacher_in_charge:
            return f"{self.teacher_in_charge.first_name} {self.teacher_in_charge.last_name}".strip()
        return "No teacher assigned"

    @property
    def is_teacher_assigned(self):
        """
        Returns True if a teacher is assigned to this class.
        """
        return self.teacher_in_charge is not None