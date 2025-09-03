from rest_framework import permissions
from rest_framework.permissions import BasePermission

class IsAdminOrTeacher(permissions.BasePermission):
    """
    Custom permission to only allow Admins and Teachers to access class management.
    
    This permission checks if the user has either ADMIN or TEACHER role.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            bool: True if user has ADMIN or TEACHER role, False otherwise
        """
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has a role attribute
        if not hasattr(request.user, 'role'):
            return False
        
        # Allow access for ADMIN and TEACHER roles
        return request.user.role in ['ADMIN', 'TEACHER']
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access a specific object.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            obj: The object being accessed
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        # First check basic permission
        if not self.has_permission(request, view):
            return False
        
        # For Class objects, allow ADMIN full access
        if request.user.role == 'ADMIN':
            return True
        
        # For TEACHER role, allow access to all classes
        # (Teachers can manage any class, not just their own)
        if request.user.role == 'TEACHER':
            return True
        
        return False


class IsAdminOrTeacherReadOnly(permissions.BasePermission):
    """
    Custom permission to allow Admins full access and Teachers read-only access.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role'):
            return False
        
        # Allow access for ADMIN and TEACHER roles
        return request.user.role in ['ADMIN', 'TEACHER']
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions.
        """
        if not self.has_permission(request, view):
            return False
        
        # ADMIN has full access
        if request.user.role == 'ADMIN':
            return True
        
        # TEACHER has read-only access
        if request.user.role == 'TEACHER':
            return request.method in permissions.SAFE_METHODS
        
        return False


class IsTeacherInCharge(permissions.BasePermission):
    """
    Custom permission to allow only the teacher assigned to a class to modify it.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has basic permission to access the view.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role'):
            return False
        
        # Allow access for ADMIN and TEACHER roles
        return request.user.role in ['ADMIN', 'TEACHER']
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user is the teacher in charge of the class.
        """
        if not self.has_permission(request, view):
            return False
        
        # ADMIN has full access
        if request.user.role == 'ADMIN':
            return True
        
        # TEACHER can only modify classes they are in charge of
        if request.user.role == 'TEACHER':
            # Read access for all teachers
            if request.method in permissions.SAFE_METHODS:
                return True
            
            # Write access only for teacher in charge
            return obj.teacher_in_charge == request.user
        
        return False


class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow Admins.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user is an admin.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role'):
            return False
        
        return request.user.role == 'ADMIN'
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level admin permission.
        """
        return self.has_permission(request, view)


class IsTeacherUser(BasePermission):
    """
    Allows access only to users with the 'TEACHER' role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'TEACHER'


def has_role(user, roles):
    """
    Utility function to check if a user has any of the specified roles.
    
    Args:
        user: The user object
        roles: List of roles to check against
        
    Returns:
        bool: True if user has any of the specified roles
    """
    if not user or not user.is_authenticated:
        return False
    
    if not hasattr(user, 'role'):
        return False
    
    if isinstance(roles, str):
        roles = [roles]
    
    return user.role in roles


# Permission combinations for common use cases
class AdminOrTeacherPermissions:
    """
    Class to combine common permission patterns.
    """
    
    @staticmethod
    def get_permissions():
        """
        Get standard admin or teacher permissions.
        """
        return [IsAdminOrTeacher]
    
    @staticmethod
    def get_read_only_permissions():
        """
        Get read-only permissions for admin or teacher.
        """
        return [IsAdminOrTeacherReadOnly]
    
    @staticmethod
    def get_teacher_in_charge_permissions():
        """
        Get permissions for teacher in charge.
        """
        return [IsTeacherInCharge]