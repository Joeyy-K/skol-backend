from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from students.models import StudentProfile 

class ParentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile',
        limit_choices_to={'role': 'PARENT'}
    )
    
    children = models.ManyToManyField(
        StudentProfile,
        related_name='parents',
        blank=True 
    )
    
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__full_name']
    
    def __str__(self):
        return f"Profile for Parent: {self.user.full_name}"

    def clean(self):
        """Validate that the linked user has a PARENT role."""
        if self.user and self.user.role != 'PARENT':
            raise ValidationError("ParentProfile can only be linked to users with a PARENT role.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)