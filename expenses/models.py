from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class ExpenseCategory(models.Model):
    """
    Model for categorizing expenses.
    e.g., Salaries, Utilities, Maintenance, Supplies.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Name of the expense category")
    description = models.TextField(blank=True, help_text="Optional description for the category")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Expense(models.Model):
    """
    Model to record a single expense transaction.
    """
    description = models.CharField(max_length=255, help_text="A brief description of the expense")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="The amount of the expense")
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expenses',
        help_text="The category of this expense"
    )
    expense_date = models.DateField(default=timezone.now, help_text="The date the expense was incurred")
    receipt = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True, help_text="Optional receipt attachment")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_expenses',
        help_text="User who recorded this expense"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.description} - {self.amount} on {self.expense_date}"

    def clean(self):
        if self.amount <= Decimal('0.00'):
            raise ValidationError({'amount': 'Expense amount must be positive.'})