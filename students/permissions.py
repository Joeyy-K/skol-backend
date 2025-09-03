# students/permissions.py
from rest_framework.permissions import BasePermission
from auth_system.permissions import IsAdminUser, IsTeacherUser, IsAdminOrTeacher

class IsAdminOrTeacher(BasePermission):
    """Permission for Admin or Teacher users"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'TEACHER']
        )


class StudentProfilePermission(BasePermission):
    """
    Custom permission for StudentProfile:
    - Admin/Teacher: Full access to all profiles
    - Student: Can only view/update their own profile (limited fields)
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role in ['ADMIN', 'TEACHER']:
            return True
        
        if request.user.role == 'STUDENT':
            return obj.user == request.user
        
        return False

class IsClassTeacherOrAdmin(BasePermission):
    """
    Object-level permission to allow access only to Admins or to a Teacher
    who is in charge of the student's assigned class.
    """
    def has_permission(self, request, view):
        return IsAdminOrTeacher().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is an admin or the student's class teacher.
        `obj` here is the StudentProfile instance.
        """
        user = request.user

        if user.role == 'ADMIN':
            return True
        
        if not obj.classroom or user.role != 'TEACHER':
            return False

        return obj.classroom.teacher_in_charge == user