# exams/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Exam, StudentScore, Term

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'start_date']
    search_fields = ['name']
    ordering = ['-start_date']


class StudentScoreInline(admin.TabularInline):
    model = StudentScore
    extra = 0
    fields = ['student', 'score', 'percentage_display', 'grade_display', 'remarks']
    readonly_fields = ['percentage_display', 'grade_display']
    
    def percentage_display(self, obj):
        if obj.id:
            return f"{obj.percentage}%"
        return "-"
    percentage_display.short_description = "Percentage"
    
    def grade_display(self, obj):
        if obj.id:
            return obj.grade
        return "-"
    grade_display.short_description = "Grade"


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'subject', 'classroom', 'date', 'term', 
        'max_score', 'total_students_display', 'average_score_display', 'created_by'
    ]
    list_filter = ['subject', 'classroom', 'term', 'date', 'created_by']
    search_fields = ['name', 'subject__name', 'classroom__name']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    inlines = [StudentScoreInline]
    
    fieldsets = (
        ('Exam Information', {
            'fields': ('name', 'subject', 'classroom', 'date', 'max_score')
        }),
        ('Additional Information', {
            'fields': ('term', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def total_students_display(self, obj):
        return obj.total_students
    total_students_display.short_description = "Total Students"
    
    def average_score_display(self, obj):
        avg = obj.average_score
        if avg > 0:
            return format_html(
                '<span style="color: {};">{}</span>',
                'green' if avg >= 70 else 'orange' if avg >= 50 else 'red',
                avg
            )
        return "-"
    average_score_display.short_description = "Average Score"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StudentScore)
class StudentScoreAdmin(admin.ModelAdmin):
    list_display = [
        'exam', 'student', 'score', 'percentage_display', 
        'grade_display', 'remarks_short'
    ]
    list_filter = ['exam__subject', 'exam__classroom', 'exam__date']
    search_fields = [
        'exam__name', 'student__first_name', 'student__last_name', 
        'student__admission_number'
    ]
    ordering = ['-exam__date', '-score']
    
    fieldsets = (
        ('Score Information', {
            'fields': ('exam', 'student', 'score', 'remarks')
        }),
        ('Calculated Fields', {
            'fields': ('percentage_display', 'grade_display'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['percentage_display', 'grade_display']
    
    def percentage_display(self, obj):
        return f"{obj.percentage}%"
    percentage_display.short_description = "Percentage"
    
    def grade_display(self, obj):
        return obj.grade
    grade_display.short_description = "Grade"
    
    def remarks_short(self, obj):
        if obj.remarks:
            return obj.remarks[:50] + "..." if len(obj.remarks) > 50 else obj.remarks
        return "-"
    remarks_short.short_description = "Remarks"