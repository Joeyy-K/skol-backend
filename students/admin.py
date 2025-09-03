# students/admin.py
from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = [
        'admission_number',
        'get_user_email',
        'get_user_full_name',
        'classroom',
        'created_at'
    ]
    list_filter = ('classroom__level', 'classroom__name', 'created_at')
    search_fields = [
        'admission_number',
        'user__email',
        'user__full_name',
        'classroom__name',
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('user', 'admission_number', 'classroom', 'date_of_birth', 'address'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'

    def get_user_full_name(self, obj):
        return obj.user.full_name
    get_user_full_name.short_description = 'Full Name'
    get_user_full_name.admin_order_field = 'user__full_name'