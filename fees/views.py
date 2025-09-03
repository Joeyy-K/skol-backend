from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend

from classes.serializers import ClassListSerializer

from .models import FeeStructure, Invoice, InvoiceItem, Payment
from .serializers import (
    FeeStructureSerializer, InvoiceSerializer, InvoiceListSerializer,
    InvoiceItemSerializer, PaymentSerializer, InvoiceGenerationSerializer
)
from auth_system.permissions import IsAdminUser, IsParentUser
from classes.models import Class
from exams.models import Term
from students.models import StudentProfile


class FeeStructureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing fee structures.
    Only admins can create, update, delete fee structures.
    """
    queryset = FeeStructure.objects.all().order_by('classroom', 'term', 'name')
    serializer_class = FeeStructureSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['classroom', 'term']
    search_fields = ['name', 'description', 'classroom__name', 'term__name']
    ordering_fields = ['name', 'amount', 'classroom', 'term', 'created_at']
    ordering = ['classroom', 'term', 'name']

    def get_queryset(self):
        """
        Optimize queryset with select_related for better performance.
        """
        return super().get_queryset().select_related('classroom', 'term')
    
    @action(detail=False, methods=['get'])
    def grouped_by_class(self, request):
        """
        Returns a list of classes with their associated fee structures
        nested inside for a specific term. Supports filtering by class IDs.
        """
        term_id = request.query_params.get('term', None)
        class_ids_str = request.query_params.get('class_ids', None)
        
        if not term_id:
            return Response({'error': 'A term ID must be provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the classes to process
        if class_ids_str:
            try:
                class_ids = [int(id.strip()) for id in class_ids_str.split(',') if id.strip()]
                classrooms = Class.objects.filter(pk__in=class_ids)
            except ValueError:
                return Response({'error': 'Invalid class IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Fallback if no specific classes are requested
            classrooms = Class.objects.all()
        
        response_data = []
        for classroom in classrooms:
            structures = FeeStructure.objects.filter(classroom=classroom, term_id=term_id)
            
            class_serializer = ClassListSerializer(classroom)
            structure_serializer = FeeStructureSerializer(structures, many=True)
            
            response_data.append({
                'class_info': class_serializer.data,
                'fee_structures': structure_serializer.data
            })
            
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Provides statistics about fee structures for a given term.
        Expects a 'term_id' query parameter.
        """
        term_id = request.query_params.get('term_id', None)
        if not term_id:
            return Response({'error': 'A term_id must be provided.'}, status=status.HTTP_400_BAD_REQUEST)

        all_classes = Class.objects.all()
        all_class_ids = [c.id for c in all_classes]
        
        structures_for_term = FeeStructure.objects.filter(term_id=term_id)
        
        classes_with_fees_ids = structures_for_term.values_list('classroom_id', flat=True).distinct()
        
        total_classes_count = all_classes.count()
        classes_with_fees_count = FeeStructure.objects.filter(
            term_id=term_id
        ).values('classroom_id').distinct().count()
        classes_without_fees_count = total_classes_count - classes_with_fees_count
        
        total_potential_revenue = structures_for_term.aggregate(total=Sum('amount'))['total'] or 0

        stats_data = {
            'total_classes': total_classes_count,
            'classes_with_fees': classes_with_fees_count,
            'classes_without_fees': classes_without_fees_count,
            'total_potential_revenue': total_potential_revenue
        }
        
        return Response(stats_data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices.
    Admins can do anything. Parents can only view their children's invoices.
    """
    queryset = Invoice.objects.all().order_by('-issue_date', '-created_at')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['student', 'classroom', 'term', 'status', 'term__academic_year']
    search_fields = ['student__user__full_name', 'student__admission_number', 'classroom__name']
    ordering_fields = ['issue_date', 'due_date', 'total_amount', 'status', 'created_at']
    ordering = ['-issue_date', '-created_at']

    def get_serializer_class(self):
        """
        Use different serializers for list and detail views.
        """
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceSerializer

    def get_queryset(self):
        """
        Filter queryset based on user role and prefetch related data.
        Uses prefetch_related for significant performance boost - fetches all related 
        items and payments in just two extra queries instead of one query per invoice.
        """
        queryset = Invoice.objects.select_related(
            'student__user', 'classroom', 'term'
        ).prefetch_related(
            'items', 'payments__recorded_by'  
        )
        
        user = self.request.user
        
        if user.role == 'ADMIN':
            return queryset.order_by('-due_date', '-created_at')
        elif user.role == 'PARENT':
            try:
                parent_profile = user.parent_profile
                children_ids = parent_profile.children.values_list('id', flat=True)
                return queryset.filter(student_id__in=children_ids).order_by('-due_date', '-created_at')
            except user.parent_profile.DoesNotExist:
                return queryset.none()
        else:
            return queryset.none()

    def get_permissions(self):
        """
        Assign permissions based on action and user role.
        """
        if self.action in ['list', 'retrieve']:
            class CanViewInvoices(IsAuthenticated):
                def has_permission(self, request, view):
                    return (super().has_permission(request, view) and 
                           request.user.role in ['ADMIN', 'PARENT'])
            return [CanViewInvoices()]
        else:
            return [IsAdminUser()]
        
    @action(detail=False, methods=['post'])
    def generate_invoices(self, request):
        """
        Custom action to generate invoices for all students in a class for a specific term.
        """
        serializer = InvoiceGenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        class_id = serializer.validated_data['class_id']
        term_id = serializer.validated_data['term_id']
        
        classroom = get_object_or_404(Class, id=class_id)
        term = get_object_or_404(Term, id=term_id)
        
        fee_structures = FeeStructure.objects.filter(
            classroom=classroom,
            term=term
        )
        
        if not fee_structures.exists():
            return Response(
                {'error': 'No fee structures found for the specified class and term.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        students = StudentProfile.objects.filter(classroom=classroom)
        
        if not students.exists():
            return Response(
                {'error': 'No students found in the specified class.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        existing_invoices = Invoice.objects.filter(
            classroom=classroom,
            term=term
        ).count()
        
        if existing_invoices > 0:
            return Response(
                {
                    'error': f'{existing_invoices} invoices already exist for this class and term. '
                             'Please delete existing invoices before generating new ones.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_invoices = []
        failed_students = []
        
        due_date = datetime.now().date() + timedelta(days=30)
        
        with transaction.atomic():
            for student in students:
                try:
                    total_amount = sum(fs.amount for fs in fee_structures)
                    
                    invoice = Invoice.objects.create(
                        student=student,
                        classroom=classroom,
                        term=term,
                        due_date=due_date,
                        total_amount=total_amount,
                        status='UNPAID'
                    )
                    
                    invoice_items = []
                    for fee_structure in fee_structures:
                        invoice_item = InvoiceItem(
                            invoice=invoice,
                            description=f"{fee_structure.name} - {term.name}",
                            amount=fee_structure.amount
                        )
                        invoice_items.append(invoice_item)
                    
                    InvoiceItem.objects.bulk_create(invoice_items)
                    
                    created_invoices.append(invoice.id)
                    
                except Exception as e:
                    failed_students.append({
                        'student_id': student.id,
                        'student_name': student.user.full_name,
                        'error': str(e)
                    })
        
        response_data = {
            'message': f'Invoice generation completed for {classroom.name} - {term.name}',
            'summary': {
                'total_students': students.count(),
                'invoices_created': len(created_invoices),
                'failed_students': len(failed_students),
                'total_fee_structures': fee_structures.count(),
                'due_date': due_date.isoformat()
            },
            'created_invoice_ids': created_invoices
        }
        
        if failed_students:
            response_data['failed_students'] = failed_students
        
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get all overdue invoices.
        """
        from django.utils import timezone
        
        overdue_invoices = self.get_queryset().filter(
            due_date__lt=timezone.now().date(),
            status__in=['UNPAID', 'PARTIALLY_PAID']
        )
        
        page = self.paginate_queryset(overdue_invoices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(overdue_invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary_stats(self, request):
        """
        Get summary statistics for invoices.
        """
        queryset = self.get_queryset()
        
        total_invoices = queryset.count()
        paid_invoices = queryset.filter(status='PAID').count()
        unpaid_invoices = queryset.filter(status='UNPAID').count()
        partially_paid_invoices = queryset.filter(status='PARTIALLY_PAID').count()
        overdue_invoices = queryset.filter(status='OVERDUE').count()
        
        from django.db.models import Sum
        total_amount = queryset.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        total_paid = queryset.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_outstanding = total_amount - total_paid
        
        stats = {
            'invoice_counts': {
                'total': total_invoices,
                'paid': paid_invoices,
                'unpaid': unpaid_invoices,
                'partially_paid': partially_paid_invoices,
                'overdue': overdue_invoices
            },
            'amounts': {
                'total_invoiced': float(total_amount),
                'total_paid': float(total_paid),
                'total_outstanding': float(total_outstanding)
            },
            'percentages': {
                'paid_percentage': round((paid_invoices / total_invoices * 100), 2) if total_invoices > 0 else 0,
                'collection_rate': round((total_paid / total_amount * 100), 2) if total_amount > 0 else 0
            }
        }
        
        return Response(stats)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.
    Only admins can create, update, delete payments.
    """
    queryset = Payment.objects.all().order_by('-payment_date', '-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['invoice', 'payment_method', 'recorded_by', 'payment_date']
    search_fields = ['reference_code', 'invoice__student__user__full_name', 'notes']
    ordering_fields = ['payment_date', 'amount', 'payment_method', 'created_at']
    ordering = ['-payment_date', '-created_at']

    def get_queryset(self):
        """
        Optimize queryset with select_related for better performance.
        """
        return super().get_queryset().select_related(
            'invoice__student__user', 'invoice__classroom', 
            'invoice__term', 'recorded_by'
        )

    def perform_create(self, serializer):
        """
        Set recorded_by to current user when creating a payment.
        """
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        """
        Keep the original recorded_by when updating a payment.
        """
        serializer.save()

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent payments (last 30 days).
        """
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_payments = self.get_queryset().filter(payment_date__gte=thirty_days_ago)
        
        page = self.paginate_queryset(recent_payments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_method(self, request):
        """
        Get payment statistics grouped by payment method.
        """
        from django.db.models import Sum, Count
        
        stats = self.get_queryset().values('payment_method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')
        
        return Response({
            'payment_method_stats': list(stats)
        })