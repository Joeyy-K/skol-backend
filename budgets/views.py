from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from collections import defaultdict

from .models import Budget
from .serializers import BudgetSerializer
from expenses.models import Expense, ExpenseCategory
from auth_system.permissions import IsAdminUser

class BudgetViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing budgets.
    """
    queryset = Budget.objects.all().select_related('category')
    serializer_class = BudgetSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['year', 'month', 'category']

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert_budget(self, request):
        """
        Create or update a budget entry. More efficient for grid-based UIs.
        Expects: {"category": 1, "year": 2025, "month": 9, "amount": 50000}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        budget, created = Budget.objects.update_or_create(
            category=data['category'],
            year=data['year'],
            month=data['month'],
            defaults={'amount': data['amount']}
        )
        
        return Response(self.get_serializer(budget).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Provides a 'Budget vs. Actual' summary for a given year.
        """
        try:
            year = int(request.query_params.get('year'))
        except (TypeError, ValueError):
            return Response({'error': 'A valid year parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        budgets = Budget.objects.filter(year=year)
        budget_map = defaultdict(lambda: defaultdict(float))
        for b in budgets:
            budget_map[b.category.name][b.month] = float(b.amount)

        expenses = Expense.objects.filter(expense_date__year=year)\
            .values('category__name', 'expense_date__month')\
            .annotate(total_actual=Sum('amount'))
        
        actual_map = defaultdict(lambda: defaultdict(float))
        for e in expenses:
            actual_map[e['category__name']][e['expense_date__month']] = float(e['total_actual'])
            
        all_categories = ExpenseCategory.objects.all().order_by('name')
        summary_data = []

        for category in all_categories:
            cat_data = {'category_name': category.name, 'months': []}
            for month in range(1, 13):
                budget_amount = budget_map[category.name][month]
                actual_amount = actual_map[category.name][month]
                variance = budget_amount - actual_amount
                
                cat_data['months'].append({
                    'month': month,
                    'budget': budget_amount,
                    'actual': actual_amount,
                    'variance': variance
                })
            summary_data.append(cat_data)
            
        return Response(summary_data)