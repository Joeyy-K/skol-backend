# auth_system/permissions.py
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Permission class to check if the user has ADMIN role.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'ADMIN'
        )


class IsTeacherUser(BasePermission):
    """
    Permission class to check if the user has TEACHER role.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'TEACHER'
        )


class IsStudentUser(BasePermission):
    """
    Permission class to check if the user has STUDENT role.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'STUDENT'
        )


class IsParentUser(BasePermission):
    """
    Permission class to check if the user has PARENT role.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'PARENT'
        )


class IsAdminOrTeacher(BasePermission):
    """
    Permission class to check if the user is either ADMIN or TEACHER.
    Useful for management-level operations.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'TEACHER']
        )


class IsAdminOrOwner(BasePermission):
    """
    Permission class to check if the user is ADMIN or the owner of the object.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'ADMIN':
            return True
        
        try:
            if hasattr(obj, 'user'):
                return obj.user == request.user
        except AttributeError:
            return False

        return obj == request.user


class IsTeacherOrStudentOwner(BasePermission):
    """
    Permission class for scenarios where teachers can access all data,
    but students can only access their own data.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['TEACHER', 'STUDENT']

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'TEACHER':
            return True
        
        if request.user.role == 'STUDENT':
            if hasattr(obj, 'student') and obj.student == request.user:
                return True
            if hasattr(obj, 'user') and obj.user == request.user:
                return True
            return obj == request.user
        
        return False
