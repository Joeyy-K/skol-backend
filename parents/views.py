from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg
from django.db import transaction
from .models import ParentProfile
from .serializers import ParentProfileSerializer, LinkStudentSerializer
from auth_system.permissions import IsAdminUser
from students.models import StudentProfile
from students.serializers import StudentProfileSerializer


class ParentProfilePagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class ParentProfileViewSet(viewsets.ModelViewSet):
    """
    Enhanced ViewSet for Admins to manage Parent profiles with improved UX.
    """
    queryset = ParentProfile.objects.prefetch_related(
        'user', 'children__user'
    ).annotate(
        children_count=Count('children')
    ).all()
    serializer_class = ParentProfileSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__full_name', 'user__email', 'phone_number']
    pagination_class = ParentProfilePagination

    def get_queryset(self):
        """Enhanced queryset with additional filtering options."""
        queryset = super().get_queryset()
        
        # Filter by children count
        has_children = self.request.query_params.get('has_children')
        if has_children is not None:
            if has_children.lower() == 'true':
                queryset = queryset.filter(children_count__gt=0)
            elif has_children.lower() == 'false':
                queryset = queryset.filter(children_count=0)
        
        # Filter by phone number presence
        has_phone = self.request.query_params.get('has_phone')
        if has_phone is not None:
            if has_phone.lower() == 'true':
                queryset = queryset.exclude(phone_number__in=['', None])
            elif has_phone.lower() == 'false':
                queryset = queryset.filter(Q(phone_number='') | Q(phone_number__isnull=True))
        
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'], url_path='statistics')
    def get_statistics(self, request):
        """Get parent management statistics."""
        total_parents = ParentProfile.objects.count()
        parents_with_children = ParentProfile.objects.filter(children__isnull=False).distinct().count()
        parents_without_children = total_parents - parents_with_children
        avg_children_per_parent = ParentProfile.objects.annotate(
            children_count=Count('children')
        ).aggregate(avg=Avg('children_count'))['avg'] or 0
        
        return Response({
            'total_parents': total_parents,
            'parents_with_children': parents_with_children,
            'parents_without_children': parents_without_children,
            'average_children_per_parent': round(avg_children_per_parent, 2)
        })

    @action(detail=False, methods=['get'], url_path='available-students')
    def available_students(self, request):
        """Get students available for linking with search and pagination."""
        search_query = request.query_params.get('search', '').strip()
        parent_id = request.query_params.get('exclude_parent', None)
        
        # Get students not linked to the specified parent (if provided)
        queryset = StudentProfile.objects.select_related('user').all()
        
        if parent_id:
            try:
                parent = ParentProfile.objects.get(pk=parent_id)
                linked_student_ids = parent.children.values_list('id', flat=True)
                queryset = queryset.exclude(id__in=linked_student_ids)
            except ParentProfile.DoesNotExist:
                pass
        
        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(admission_number__icontains=search_query)
            )
        
        # Limit results to prevent overwhelming the frontend
        queryset = queryset[:20]
        
        serializer = StudentProfileSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-child')
    def add_child(self, request, pk=None):
        """Enhanced child linking with validation."""
        parent_profile = self.get_object()
        serializer = LinkStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        student_id = serializer.validated_data['student_id']
        
        try:
            student_profile = StudentProfile.objects.select_related('user').get(pk=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already linked
        if parent_profile.children.filter(id=student_id).exists():
            return Response(
                {'error': f'{student_profile.user.full_name} is already linked to this parent.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if student already has maximum parents (optional business rule)
        max_parents_per_student = 2  # Configurable
        current_parent_count = student_profile.parents.count()
        if current_parent_count >= max_parents_per_student:
            return Response(
                {
                    'error': f'{student_profile.user.full_name} already has the maximum number of parents linked ({max_parents_per_student}).'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            parent_profile.children.add(student_profile)
            
        return Response({
            'status': 'success',
            'message': f'Successfully linked {student_profile.user.full_name} to {parent_profile.user.full_name}.',
            'student_info': {
                'id': student_profile.id,
                'name': student_profile.user.full_name,
                'email': student_profile.user.email,
                'admission_number': student_profile.admission_number
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-child')
    def remove_child(self, request, pk=None):
        """Enhanced child unlinking with validation."""
        parent_profile = self.get_object()
        serializer = LinkStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        student_id = serializer.validated_data['student_id']
        
        try:
            student_profile = StudentProfile.objects.select_related('user').get(pk=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if actually linked
        if not parent_profile.children.filter(id=student_id).exists():
            return Response(
                {'error': f'{student_profile.user.full_name} is not linked to this parent.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            parent_profile.children.remove(student_profile)
            
        return Response({
            'status': 'success',
            'message': f'Successfully unlinked {student_profile.user.full_name} from {parent_profile.user.full_name}.'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='bulk-add-children')
    def bulk_add_children(self, request, pk=None):
        """Add multiple children to a parent at once."""
        parent_profile = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids or not isinstance(student_ids, list):
            return Response(
                {'error': 'student_ids must be a non-empty list.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all student IDs
        existing_students = StudentProfile.objects.filter(id__in=student_ids)
        if existing_students.count() != len(student_ids):
            return Response(
                {'error': 'One or more student IDs are invalid.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for already linked students
        already_linked = parent_profile.children.filter(id__in=student_ids)
        if already_linked.exists():
            linked_names = [s.user.full_name for s in already_linked]
            return Response(
                {'error': f'Students already linked: {", ".join(linked_names)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            parent_profile.children.add(*existing_students)
            
        linked_names = [s.user.full_name for s in existing_students]
        return Response({
            'status': 'success',
            'message': f'Successfully linked {len(student_ids)} students to {parent_profile.user.full_name}.',
            'linked_students': linked_names
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Enhanced delete with better error handling."""
        profile = self.get_object()
        user_full_name = profile.user.full_name
        children_count = profile.children.count()
        
        # Optional: Prevent deletion if parent has linked children
        prevent_deletion_with_children = request.query_params.get('force') != 'true'
        if prevent_deletion_with_children and children_count > 0:
            return Response(
                {
                    'error': f'Cannot delete parent {user_full_name} who has {children_count} linked student(s). Unlink students first or use force=true parameter.',
                    'children_count': children_count
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Unlink all children first
                profile.children.clear()
                # Delete user (which will cascade delete the profile)
                profile.user.delete()
                
            return Response(
                {
                    "message": f"Parent '{user_full_name}' and their profile deleted successfully.",
                    "children_unlinked": children_count
                },
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete parent: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )