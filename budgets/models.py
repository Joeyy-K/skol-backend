from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from expenses.models import ExpenseCategory
from decimal import Decimal

class Budget(models.Model):
    """
    Stores the budgeted amount for an expense category for a specific month and year.
    """
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.CASCADE, 
        related_name='budgets'
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2020)],
        help_text="The year this budget applies to (e.g., 2025)"
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="The month this budget applies to (1=Jan, 12=Dec)"
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="The budgeted amount"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['year', 'month', 'category__name']
        unique_together = ['category', 'year', 'month'] 

    def __str__(self):
        return f"Budget for {self.category.name} - {self.year}-{self.month:02d}: {self.amount}"