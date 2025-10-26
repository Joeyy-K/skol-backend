from rest_framework import serializers
from .models import ExpenseCategory, Expense
from auth_system.serializers import UserSerializer

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'created_at']

class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'description', 'amount', 'category', 'category_name',
            'expense_date', 'receipt', 'recorded_by', 'recorded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['recorded_by', 'recorded_by_name']