from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class FeeStructure(models.Model):
    """
    Model representing a fee structure for a specific class and term.
    Defines the types of fees applicable to students in a particular class during a term.
    """
    name = models.CharField(
        max_length=100,
        help_text="Name of the fee type, e.g., 'Standard Tuition Fee', 'Bus Transportation Fee'"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the fee"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Fee amount"
    )
    classroom = models.ForeignKey(
        'classes.Class',
        on_delete=models.CASCADE,
        related_name='fee_structures',
        help_text="Class this fee applies to"
    )
    term = models.ForeignKey(
        'exams.Term',
        on_delete=models.CASCADE,
        related_name='fee_structures',
        help_text="Academic term this fee applies to"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'classroom', 'term')
        verbose_name = "Fee Structure"
        verbose_name_plural = "Fee Structures"
        ordering = ['classroom', 'term', 'name']
        indexes = [
            models.Index(fields=['classroom', 'term']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.classroom.name} ({self.term})"

    def clean(self):
        """Validate fee amount is positive"""
        super().clean()
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Fee amount must be greater than zero.'
            })


class Invoice(models.Model):
    """
    Model representing an invoice for a student's fees.
    Contains multiple invoice items and tracks payment status.
    """
    STATUS_CHOICES = (
        ('UNPAID', 'Unpaid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
    )

    student = models.ForeignKey(
        'students.StudentProfile',
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="Student this invoice belongs to"
    )
    classroom = models.ForeignKey(
        'classes.Class',
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="Class the student was in when invoice was generated"
    )
    term = models.ForeignKey(
        'exams.Term',
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="Academic term this invoice applies to"
    )
    issue_date = models.DateField(
        auto_now_add=True,
        help_text="Date when the invoice was generated"
    )
    due_date = models.DateField(
        help_text="Payment due date"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total invoice amount (sum of all items)"
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount paid so far"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UNPAID',
        help_text="Current payment status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'term']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['issue_date']),
        ]

    def __str__(self):
        return f"Invoice #{self.id} - {self.student.user.full_name} ({self.term})"

    @property
    def balance(self):
        """Calculate remaining balance (total_amount - amount_paid)"""
        return self.total_amount - self.amount_paid

    def update_status(self):
        """
        Automatically update the invoice status based on balance and due date.
        Should be called after payments are made or when checking overdue invoices.
        """
        balance = self.balance
        today = timezone.now().date()

        if balance <= 0:
            self.status = 'PAID'
        elif balance == self.total_amount:
            if today > self.due_date:
                self.status = 'OVERDUE'
            else:
                self.status = 'UNPAID'
        else:
            if today > self.due_date:
                self.status = 'OVERDUE'
            else:
                self.status = 'PARTIALLY_PAID'

    def clean(self):
        """Validate invoice data"""
        super().clean()
        
        if self.total_amount <= 0:
            raise ValidationError({
                'total_amount': 'Total amount must be greater than zero.'
            })
        
        if self.amount_paid < 0:
            raise ValidationError({
                'amount_paid': 'Amount paid cannot be negative.'
            })
        
        if self.amount_paid > self.total_amount:
            raise ValidationError({
                'amount_paid': 'Amount paid cannot exceed total amount.'
            })
        
        if not self.pk and self.due_date < timezone.now().date():
            raise ValidationError({
                'due_date': 'Due date cannot be in the past.'
            })

    def save(self, *args, **kwargs):
        """Override save to update status and validate data"""
        self.full_clean()
        
        if self.pk:  
            self.update_status()
        
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    """
    Model representing a single line item on an invoice.
    Each item represents a specific fee with its description and amount.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Invoice this item belongs to"
    )
    description = models.CharField(
        max_length=200,
        help_text="Description of the fee item, e.g., 'Term 1 Tuition'"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount for this specific item"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Invoice Item"
        verbose_name_plural = "Invoice Items"
        ordering = ['invoice', 'description']

    def __str__(self):
        return f"{self.description} - {self.amount}"

    def clean(self):
        """Validate item amount is positive"""
        super().clean()
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Item amount must be greater than zero.'
            })


class Payment(models.Model):
    """
    Model representing a payment made against an invoice.
    Records payment details and tracks who recorded the payment.
    """
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Invoice this payment is for"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    payment_date = models.DateField(
        help_text="Date the payment was made"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Method used for payment"
    )
    reference_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Transaction ID or reference code (optional)"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_payments',
        help_text="Admin/staff who recorded this payment"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the payment"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice', 'payment_date']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['recorded_by']),
        ]

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} ({self.payment_date})"

    def clean(self):
        """Validate payment data"""
        super().clean()
        
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Payment amount must be greater than zero.'
            })
        
        if self.payment_date > timezone.now().date():
            raise ValidationError({
                'payment_date': 'Payment date cannot be in the future.'
            })
        
        if not self.pk and self.invoice:
            current_balance = self.invoice.balance
            if self.amount > current_balance:
                raise ValidationError({
                    'amount': f'Payment amount ({self.amount}) cannot exceed invoice balance ({current_balance}).'
                })

    def save(self, *args, **kwargs):
        """Override save to update invoice amount_paid and status"""
        is_new = not self.pk
        old_amount = None
        
        if not is_new:
            old_payment = Payment.objects.get(pk=self.pk)
            old_amount = old_payment.amount
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        if is_new:
            self.invoice.amount_paid += self.amount
        else:
            self.invoice.amount_paid = self.invoice.amount_paid - old_amount + self.amount
        
        self.invoice.update_status()
        self.invoice.save()

    def delete(self, *args, **kwargs):
        """Override delete to update invoice amount_paid"""
        invoice = self.invoice
        amount = self.amount
        
        super().delete(*args, **kwargs)
        
        invoice.amount_paid -= amount
        invoice.update_status()
        invoice.save()