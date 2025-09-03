from rest_framework.permissions import BasePermission
from classes.models import Class

class CanViewAttendance(BasePermission):
    """
    Permission to allow all teachers to view attendance data,
    but only admins and assigned teachers can edit.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users can always view attendance
        if request.user.role == 'ADMIN':
            return True
        
        # All teachers can view attendance data
        if request.user.role == 'TEACHER':
            return True
        
        return False

class IsTeacherInChargeOrAdmin(BasePermission):
    """
    Permission to only allow Admins or the Teacher in charge of the requested class
    to edit attendance for that class. All teachers can view.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users can always edit attendance
        if request.user.role == 'ADMIN':
            return True
        
        if request.user.role == 'TEACHER':
            # For viewing (GET requests), all teachers are allowed
            if request.method == 'GET':
                return True
            
            # For editing (POST, PUT, PATCH, DELETE), only assigned teacher
            class_id_str = request.data.get('class_id') or request.query_params.get('class_id')
            if not class_id_str:
                return False
            
            try:
                class_id = int(class_id_str)
                return Class.objects.filter(pk=class_id, teacher_in_charge=request.user).exists()
            except (ValueError, TypeError):
                return False
        
        return False

class CanEditAttendance(BasePermission):
    """
    Specific permission for editing attendance records.
    Only allows admins and assigned teachers to make changes.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.role == 'ADMIN':
            return True
        
        if request.user.role == 'TEACHER':
            class_id_str = request.data.get('class_id') or request.query_params.get('class_id')
            if not class_id_str:
                return False
            
            try:
                class_id = int(class_id_str)
                classroom = Class.objects.get(pk=class_id)
                return classroom.teacher_in_charge == request.user
            except (ValueError, TypeError, Class.DoesNotExist):
                return False
        
        return False

class AttendanceHistoryPermission(BasePermission):
    """
    Permission for viewing attendance history.
    All teachers can view, with some restrictions on cross-class access for regular teachers.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users can view all attendance history
        if request.user.role == 'ADMIN':
            return True
        
        # Teachers can view attendance history
        if request.user.role == 'TEACHER':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission for specific attendance records.
        """
        if request.user.role == 'ADMIN':
            return True
        
        if request.user.role == 'TEACHER':
            # Teachers can view records from any class, but this could be restricted
            # if you want to limit teachers to only their assigned classes
            return True
        
        return False