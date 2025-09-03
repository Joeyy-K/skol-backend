# reports/models.py
from django.db import models
from django.conf import settings
from students.models import StudentProfile
from exams.models import Term, Exam


class Report(models.Model):
    """Model to store generated report cards as official, unchangeable records"""
    
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='reports',
        help_text="Student for whom this report is generated"
    )
    
    term = models.ForeignKey(
        Term, 
        on_delete=models.CASCADE, 
        related_name='reports',
        help_text="Academic term for this report"
    )
    
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.CASCADE, 
        related_name='reports',
        null=True, 
        blank=True,
        help_text="Specific exam (optional - for single-exam reports vs end-of-term summaries)"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Report title, e.g., 'Term 1 Mid-Term Report' or 'Term 1 Final Report Card'"
    )
    
    report_data = models.JSONField(
        help_text="Complete serialized JSON of the report card at generation time"
    )
    
    is_published = models.BooleanField(
        default=False,
        help_text="Controls visibility for parents and students"
    )
    
    generated_by = models.ForeignKey(
        'auth_system.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports',
        help_text="User who generated this report"
    )
    
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when report was generated"
    )
    
    class Meta:
        ordering = ['-generated_at', 'student__admission_number']
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'term', 'exam'],
                name='unique_student_term_exam_report',
                condition=models.Q(exam__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['student', 'term'],
                name='unique_student_term_summary_report',
                condition=models.Q(exam__isnull=True)
            )
        ]
    
    def __str__(self):
        if self.exam:
            return f"{self.student.admission_number} - {self.title} ({self.exam.name})"
        return f"{self.student.admission_number} - {self.title}"
    
    @property
    def report_type(self):
        """Returns the type of report - either 'Exam Report' or 'Term Summary'"""
        return "Exam Report" if self.exam else "Term Summary"
    
    @property
    def student_name(self):
        """Get student's full name"""
        return self.student.user.full_name
    
    @property
    def term_display(self):
        """Get formatted term display"""
        return self.term.display_name
    
    def save(self, *args, **kwargs):
        """Override save to ensure data integrity"""
        if self.exam and self.exam.term_id != self.term.id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Exam must belong to the same term as the report")
        
        super().save(*args, **kwargs)