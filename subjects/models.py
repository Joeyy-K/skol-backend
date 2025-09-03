from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Subject(models.Model):
    """
    Model representing a school subject.
    
    A subject can have a teacher in charge and is associated with specific grade levels.
    """
    
    name = models.CharField(
        max_length=100,
        help_text="The name of the subject (e.g., Mathematics, English)"
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique subject code (e.g., MATH101, ENG201)"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the subject"
    )
    
    level = models.CharField(
        max_length=50,
        help_text="Grade level or academic level (e.g., Grade 1, Grade 2, High School)"
    )
    
    teacher_in_charge = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'TEACHER', 'is_active': True},
        related_name='subjects_in_charge',
        help_text="Teacher responsible for this subject"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the subject was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the subject was last updated"
    )
    
    class Meta:
        ordering = ['level', 'name']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        db_table = 'subjects'
        
        # Add database constraints
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'level'],
                name='unique_subject_per_level'
            )
        ]
    
    def __str__(self):
        """String representation of the Subject model."""
        return f"{self.name} - {self.level}"
    
    @property
    def teacher_name(self):
        """
        Property to get the full name of the teacher in charge.
        
        Returns:
            str: Full name of the teacher or 'No teacher assigned' if none.
        """
        if self.teacher_in_charge:
            return self.teacher_in_charge.full_name or self.teacher_in_charge.email
        return "No teacher assigned"
    
    def clean(self):
        """
        Validate the model instance.
        """
        from django.core.exceptions import ValidationError
        
        # Ensure code is uppercase
        if self.code:
            self.code = self.code.upper()
        
        # Validate that teacher has the correct role if assigned
        if self.teacher_in_charge and hasattr(self.teacher_in_charge, 'role'):
            if self.teacher_in_charge.role != 'TEACHER':
                raise ValidationError({
                    'teacher_in_charge': 'Only users with TEACHER role can be assigned as teacher in charge.'
                })
            
            if not self.teacher_in_charge.is_active:
                raise ValidationError({
                    'teacher_in_charge': 'Only active teachers can be assigned as teacher in charge.'
                })
    
    def save(self, *args, **kwargs):
        """
        Override save method to run clean validation.
        """
        self.clean()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """
        Get the absolute URL for this subject.
        """
        from django.urls import reverse
        return reverse('subject-detail', kwargs={'pk': self.pk})