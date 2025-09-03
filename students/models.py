# students/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from classes.models import Class

class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    admission_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique admission number for the student"
    )
    classroom = models.ForeignKey(
        Class, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students'
    )
    date_of_birth = models.DateField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['admission_number']
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"

    def __str__(self):
        return f"{self.admission_number} - {self.user.full_name}"

    def clean(self):
        """Validate that the linked user has STUDENT role"""
        if self.user and self.user.role != 'STUDENT':
            raise ValidationError(
                "StudentProfile can only be linked to users with STUDENT role."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)