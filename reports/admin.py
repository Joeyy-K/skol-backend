# reports/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Report
import json


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Django admin configuration for Report model"""
    
    list_display = [
        'student_admission_number',
        'student_name',
        'title',
        'term_display',
        'exam_name',
        'report_type_badge',
        'is_published_badge',
        'generated_by',
        'generated_at'
    ]
    
    list_filter = [
        'is_published',
        'term__academic_year',
        'term__name',
        'generated_at',
        'exam__subject'
    ]
    
    search_fields = [
        'student__admission_number',
        'student__user__first_name',
        'student__user__last_name',
        'title',
        'exam__name'
    ]
    
    readonly_fields = [
        'student',
        'term',
        'exam',
        'title',
        'report_data_preview',
        'generated_by',
        'generated_at'
    ]
    
    fieldsets = (
        ('Report Information', {
            'fields': ('student', 'term', 'exam', 'title')
        }),
        ('Report Data', {
            'fields': ('report_data_preview',),
            'classes': ('wide',)
        }),
        ('Publication Status', {
            'fields': ('is_published',)
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'generated_at'
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        return super().get_queryset(request).select_related(
            'student__user',
            'term',
            'exam__subject',
            'generated_by'
        )
    
    def student_admission_number(self, obj):
        """Display student admission number"""
        return obj.student.admission_number
    student_admission_number.short_description = 'Admission No.'
    student_admission_number.admin_order_field = 'student__admission_number'
    
    def student_name(self, obj):
        """Display student full name"""
        return obj.student_name
    student_name.short_description = 'Student Name'
    student_name.admin_order_field = 'student__user__first_name'
    
    def term_display(self, obj):
        """Display formatted term"""
        return obj.term_display
    term_display.short_description = 'Term'
    term_display.admin_order_field = 'term__academic_year'
    
    def exam_name(self, obj):
        """Display exam name or indicate term summary"""
        if obj.exam:
            return obj.exam.name
        return '-'
    exam_name.short_description = 'Exam'
    exam_name.admin_order_field = 'exam__name'
    
    def report_type_badge(self, obj):
        """Display report type with color coding"""
        if obj.exam:
            return format_html(
                '<span style="background-color: #2196F3; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">EXAM</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">TERM</span>'
            )
    report_type_badge.short_description = 'Type'
    
    def is_published_badge(self, obj):
        """Display publication status with color coding"""
        if obj.is_published:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">✓ PUBLISHED</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #FF9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">○ DRAFT</span>'
            )
    is_published_badge.short_description = 'Status'
    is_published_badge.admin_order_field = 'is_published'
    
    def report_data_preview(self, obj):
        """Display formatted JSON preview of report data"""
        if obj.report_data:
            try:
                formatted_json = json.dumps(obj.report_data, indent=2)
                return format_html(
                    '<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 400px; overflow-y: auto;">{}</pre>',
                    formatted_json
                )
            except (TypeError, ValueError):
                return format_html(
                    '<p style="color: red;">Invalid JSON data</p>'
                )
        return format_html('<p style="color: #666;">No report data</p>')
    report_data_preview.short_description = 'Report Data (JSON)'
    
    def has_add_permission(self, request):
        """Disable manual addition through admin - reports should be generated programmatically"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion only for superusers"""
        return request.user.is_superuser
    
    def get_readonly_fields(self, request, obj=None):
        """Make most fields readonly to preserve report integrity"""
        readonly = list(self.readonly_fields)
        
        if obj and not request.user.is_superuser:
            readonly.extend(['is_published'])
        
        return readonly
    
    actions = ['publish_reports', 'unpublish_reports']
    
    def publish_reports(self, request, queryset):
        """Bulk action to publish selected reports"""
        updated = queryset.update(is_published=True)
        self.message_user(
            request,
            f'{updated} report(s) were successfully published.'
        )
    publish_reports.short_description = "Publish selected reports"
    
    def unpublish_reports(self, request, queryset):
        """Bulk action to unpublish selected reports"""
        updated = queryset.update(is_published=False)
        self.message_user(
            request,
            f'{updated} report(s) were successfully unpublished.'
        )
    unpublish_reports.short_description = "Unpublish selected reports"