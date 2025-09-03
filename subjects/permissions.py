from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'

class IsAdminOrTeacher(BasePermission):
    """
    Allows access only to users with ADMIN or TEACHER roles.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['ADMIN', 'TEACHER']
        )


class IsTeacherInCharge(BasePermission):
    """
    Object-level permission to only allow the teacher in charge to edit the subject.
    Admins are also allowed.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any authenticated user with appropriate role
        if request.method in SAFE_METHODS:
            return (
                request.user.is_authenticated and
                hasattr(request.user, 'role') and
                request.user.role in ['ADMIN', 'TEACHER']
            )

        # Write permissions for Admins or the teacher in charge
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            (
                request.user.role == 'ADMIN' or
                obj.teacher_in_charge == request.user
            )
        )
