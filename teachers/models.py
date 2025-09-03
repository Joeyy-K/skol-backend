from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        limit_choices_to={'role': 'TEACHER'}
    )
    employee_id = models.CharField(max_length=20, unique=True, help_text="Unique Employee ID")
    specialization = models.CharField(max_length=100, help_text="e.g., Mathematics, Physics, English Literature")
    date_of_hire = models.DateField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True, help_text="A short biography or a list of qualifications.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__full_name']
    
    def __str__(self):
        return f"Profile for {self.user.full_name}"

    def clean(self):
        """Validate that the linked user has a TEACHER role."""
        if self.user and self.user.role != 'TEACHER':
            raise ValidationError("TeacherProfile can only be linked to users with a TEACHER role.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)