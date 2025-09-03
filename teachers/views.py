from rest_framework import viewsets, filters, status
from rest_framework.generics import ListAPIView
from django.db.models import Q
from .models import TeacherProfile
from .serializers import TeacherProfileSerializer
from auth_system.permissions import IsAdminUser, IsParentUser, IsAdminOrTeacher
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class TeacherProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Admins to manage teacher profiles.
    """
    serializer_class = TeacherProfileSerializer
    
    def get_permissions(self):
        """
        Assigns permissions based on action.
        - Admins can do anything.
        - Parents can only list/view teachers.
        """
        if self.action in ['list', 'retrieve']:
            class IsAdminOrParent(IsAuthenticated):
                def has_permission(self, request, view):
                    return super().has_permission(request, view) and request.user.role in ['ADMIN', 'PARENT']
            return [IsAdminOrParent()]
        
        return [IsAdminUser()]
    
    def get_queryset(self):
        queryset = TeacherProfile.objects.select_related('user').all()
        
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search_query) |
                Q(employee_id__icontains=search_query) |
                Q(specialization__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
            
        return queryset.order_by('user__full_name')
    
    def destroy(self, request, *args, **kwargs):
        profile_instance = self.get_object()
        
        user_instance = profile_instance.user

        user_full_name = user_instance.full_name

        user_instance.delete()

        return Response(
            {"message": f"Teacher '{user_full_name}' and their profile have been successfully deleted."},
            status=status.HTTP_204_NO_CONTENT
        )
    
class AllTeachersListView(ListAPIView):
    """
    Provides a simple, non-paginated list of all active teachers.
    Used for populating dropdown menus in other parts of the application.
    """
    serializer_class = TeacherProfileSerializer 
    permission_classes = [IsAdminOrTeacher] 
    
    def get_queryset(self):
        return TeacherProfile.objects.filter(user__is_active=True).select_related('user').order_by('user__full_name')