from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum

from .models import ExpenseCategory, Expense
from .serializers import ExpenseCategorySerializer, ExpenseSerializer
from auth_system.permissions import IsAdminUser

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Expense Categories.
    Only accessible by Admins.
    """
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAdminUser]

class ExpenseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Expenses.
    Only accessible by Admins.
    Allows filtering by date range and category.
    """
    queryset = Expense.objects.all().select_related('category', 'recorded_by')
    serializer_class = ExpenseSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        'expense_date': ['gte', 'lte', 'exact'], 
        'category': ['exact'],
    }
    search_fields = ['description']

    def perform_create(self, serializer):
        """Automatically set the recorded_by field to the current user."""
        serializer.save(recorded_by=self.request.user)

    @action(detail=False, methods=['get'])
    def summary_by_category(self, request):
        """
        Provides a summary of total expenses grouped by category.
        Example response:
        [
            { "category__name": "Salaries", "total": 550000.00 },
            { "category__name": "Utilities", "total": 25000.00 }
        ]
        """
        from django.utils import timezone
        year = request.query_params.get('year', timezone.now().year)

        summary = Expense.objects.filter(expense_date__year=year)\
            .values('category__name')\
            .annotate(total=Sum('amount'))\
            .order_by('-total')

        for item in summary:
            if item['category__name'] is None:
                item['category__name'] = 'Uncategorized'
        
        return Response(summary)

