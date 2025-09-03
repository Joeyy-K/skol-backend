from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Class

User = get_user_model()


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """
    Admin interface for Class model with enhanced functionality.
    """
    list_display = [
        'name', 'level', 'teacher_link', 'teacher_status', 
        'created_at', 'updated_at'
    ]
    list_filter = [
        'level', 'created_at', 'updated_at',
        ('teacher_in_charge', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'name', 'level', 
        'teacher_in_charge__first_name', 
        'teacher_in_charge__last_name',
        'teacher_in_charge__email'
    ]
    ordering = ['level', 'name']
    date_hierarchy = 'created_at'
    
    # Fields organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'level')
        }),
        ('Teacher Assignment', {
            'fields': ('teacher_in_charge',),
            'description': 'Assign a teacher to be in charge of this class.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # Autocomplete and raw_id fields for better performance
    raw_id_fields = ['teacher_in_charge']
    autocomplete_fields = ['teacher_in_charge']
    
    # Custom actions
    actions = ['assign_teacher', 'remove_teacher']
    
    def get_queryset(self, request):
        """
        Optimize queryset with select_related for better performance.
        """
        return super().get_queryset(request).select_related('teacher_in_charge')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Customize the teacher_in_charge field to show only teachers.
        """
        if db_field.name == "teacher_in_charge":
            kwargs["queryset"] = User.objects.filter(
                role='TEACHER', 
                is_active=True
            ).order_by('first_name', 'last_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def teacher_link(self, obj):
        """
        Display teacher name as a clickable link to the teacher's admin page.
        """
        if obj.teacher_in_charge:
            url = reverse('admin:auth_user_change', args=[obj.teacher_in_charge.pk])
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                obj.teacher_name
            )
        return format_html('<span style="color: #999;">No teacher assigned</span>')
    
    teacher_link.short_description = 'Teacher in Charge'
    teacher_link.admin_order_field = 'teacher_in_charge__first_name'
    
    def teacher_status(self, obj):
        """
        Display teacher assignment status with color coding.
        """
        if obj.teacher_in_charge:
            if obj.teacher_in_charge.is_active:
                return format_html(
                    '<span style="color: green; font-weight: bold;">✓ Assigned</span>'
                )
            else:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⚠ Inactive Teacher</span>'
                )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Not Assigned</span>'
        )
    
    teacher_status.short_description = 'Assignment Status'
    
    def assign_teacher(self, request, queryset):
        """
        Custom admin action to assign a teacher to selected classes.
        """
        # This would typically open a form to select a teacher
        # For now, we'll just show a message
        self.message_user(
            request,
            f"Selected {queryset.count()} classes. Use individual class pages to assign teachers."
        )
    
    assign_teacher.short_description = "Assign teacher to selected classes"
    
    def remove_teacher(self, request, queryset):
        """
        Custom admin action to remove teacher assignment from selected classes.
        """
        updated_count = queryset.update(teacher_in_charge=None)
        self.message_user(
            request,
            f"Successfully removed teacher assignment from {updated_count} classes."
        )
    
    remove_teacher.short_description = "Remove teacher assignment from selected classes"
    
    def save_model(self, request, obj, form, change):
        """
        Override save_model to add custom logic if needed.
        """
        super().save_model(request, obj, form, change)
        
        # Log the action
        action = "updated" if change else "created"
        self.message_user(
            request,
            f"Class '{obj.name}' was successfully {action}."
        )
    
    def get_list_display_links(self, request, list_display):
        """
        Make the class name clickable for editing.
        """
        return ['name']
    
    # Add custom CSS and JS if needed
    class Media:
        css = {
            'all': ('admin/css/custom_class_admin.css',)  # Optional custom CSS
        }
        js = ('admin/js/custom_class_admin.js',)  # Optional custom JavaScript


# Optional: Inline admin for related models
class ClassInline(admin.TabularInline):
    """
    Inline admin for displaying classes in related model admin pages.
    """
    model = Class
    extra = 0
    fields = ['name', 'level', 'teacher_in_charge']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher_in_charge')