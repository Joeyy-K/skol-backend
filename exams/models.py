# exams/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from students.models import StudentProfile
from classes.models import Class as Classroom  

class Term(models.Model):
    """Academic Term model"""
    TERM_CHOICES = [
        ('TERM_1', 'Term 1'),
        ('TERM_2', 'Term 2'),
        ('TERM_3', 'Term 3'),
    ]
    
    name = models.CharField(max_length=20, choices=TERM_CHOICES)
    academic_year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
        help_text="Academic year (e.g., 2025)"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-academic_year', 'name']
        unique_together = ['academic_year', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['academic_year', 'name'],
                name='unique_academic_year_term'
            )
        ]
    
    def __str__(self):
        return f"{self.get_name_display()} {self.academic_year}"
    
    @property
    def display_name(self):
        """Returns a formatted display name for the term"""
        return f"{self.get_name_display()} {self.academic_year}"


class Exam(models.Model):
    """Exam model for assessments"""
    name = models.CharField(max_length=200)
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE, related_name='exams')
    classroom = models.ForeignKey('classes.Class', on_delete=models.CASCADE) 
    date = models.DateField()
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_exams'
    )
    max_score = models.IntegerField(default=100, validators=[MinValueValidator(1), MaxValueValidator(1000)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['name', 'subject', 'classroom', 'date']
    
    def __str__(self):
        return f"{self.name} - {self.subject.name} ({self.classroom.name})"
    
    @property
    def total_students(self):
        """Get total number of students who took the exam"""
        return self.scores.count()
    
    @property
    def average_score(self):
        """Calculate average score for the exam"""
        scores = self.scores.aggregate(avg_score=models.Avg('score'))
        return round(scores['avg_score'], 2) if scores['avg_score'] else 0
    
    @property
    def highest_score(self):
        """Get highest score for the exam"""
        scores = self.scores.aggregate(max_score=models.Max('score'))
        return scores['max_score'] or 0
    
    @property
    def lowest_score(self):
        """Get lowest score for the exam"""
        scores = self.scores.aggregate(min_score=models.Min('score'))
        return scores['min_score'] or 0


class StudentScore(models.Model):
    """Student scores for exams"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='scores')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='exam_scores')
    score = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    remarks = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-score']
        unique_together = ['exam', 'student']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.exam.name}: {self.score}"
    
    @property
    def percentage(self):
        """Calculate percentage score"""
        return round((float(self.score) / self.exam.max_score) * 100, 2)
    
    @property
    def grade(self):
        """Calculate letter grade based on percentage"""
        percentage = self.percentage
        if percentage >= 90:
            return 'A+'
        elif percentage >= 85:
            return 'A'
        elif percentage >= 80:
            return 'A-'
        elif percentage >= 75:
            return 'B+'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 65:
            return 'B-'
        elif percentage >= 60:
            return 'C+'
        elif percentage >= 55:
            return 'C'
        elif percentage >= 50:
            return 'C-'
        elif percentage >= 45:
            return 'D'
        else:
            return 'F'
    
    def clean(self):
        """Validate that score doesn't exceed exam's max score"""
        from django.core.exceptions import ValidationError
        if self.score and self.exam and float(self.score) > self.exam.max_score:
            raise ValidationError(f'Score cannot exceed maximum score of {self.exam.max_score}')