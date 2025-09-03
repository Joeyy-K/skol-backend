from rest_framework import serializers
from .models import FeeStructure, Invoice, InvoiceItem, Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model.
    """
    recorded_by_name = serializers.CharField(
        source='recorded_by.full_name', 
        read_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'amount', 'payment_date', 'payment_method',
            'reference_code', 'recorded_by', 'recorded_by_name', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['recorded_by', 'created_at', 'updated_at']


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Serializer for InvoiceItem model.
    """
    
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'invoice', 'description', 'amount', 'created_at'
        ]
        read_only_fields = ['created_at']


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Invoice model with nested items and payments.
    """
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    
    student_name = serializers.CharField(
        source='student.user.full_name', 
        read_only=True
    )
    student_admission_number = serializers.CharField(
        source='student.admission_number',
        read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name',
        read_only=True
    )
    term_name = serializers.CharField(
        source='term.name',
        read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'student', 'student_name', 'student_admission_number',
            'classroom', 'classroom_name', 'term', 'term_name',
            'issue_date', 'due_date', 'total_amount', 'amount_paid',
            'balance', 'status', 'items', 'payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'issue_date', 'amount_paid', 'status', 'balance',
            'student_name', 'student_admission_number', 'classroom_name',
            'term_name', 'items', 'payments', 'created_at', 'updated_at'
        ]


class FeeStructureSerializer(serializers.ModelSerializer):
    """
    Serializer for FeeStructure model.
    """
    classroom_name = serializers.CharField(
        source='classroom.name',
        read_only=True
    )
    term_name = serializers.CharField(
        source='term.name',
        read_only=True
    )
    
    class Meta:
        model = FeeStructure
        fields = [
            'id', 'name', 'description', 'amount', 'classroom',
            'classroom_name', 'term', 'term_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'classroom_name', 'term_name']


class InvoiceGenerationSerializer(serializers.Serializer):
    """
    Serializer for invoice generation custom action.
    Used to validate the class_id and term_id for bulk invoice generation.
    """
    class_id = serializers.IntegerField(
        help_text="ID of the class to generate invoices for"
    )
    term_id = serializers.IntegerField(
        help_text="ID of the term to generate invoices for"
    )
    
    def validate_class_id(self, value):
        """
        Validate that the class exists.
        """
        from classes.models import Class
        try:
            Class.objects.get(id=value)
        except Class.DoesNotExist:
            raise serializers.ValidationError("Class with this ID does not exist.")
        return value
    
    def validate_term_id(self, value):
        """
        Validate that the term exists.
        """
        from exams.models import Term
        try:
            Term.objects.get(id=value)
        except Term.DoesNotExist:
            raise serializers.ValidationError("Term with this ID does not exist.")
        return value
    
    def validate(self, data):
        """
        Validate that fee structures exist for the given class and term.
        """
        class_id = data['class_id']
        term_id = data['term_id']
        
        fee_structures = FeeStructure.objects.filter(
            classroom_id=class_id,
            term_id=term_id
        )
        
        if not fee_structures.exists():
            raise serializers.ValidationError(
                "No fee structures found for the specified class and term. "
                "Please create fee structures before generating invoices."
            )
        
        return data


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Invoice list view (without nested data).
    """
    student_name = serializers.CharField(
        source='student.user.full_name', 
        read_only=True
    )
    student_admission_number = serializers.CharField(
        source='student.admission_number',
        read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name',
        read_only=True
    )
    term_name = serializers.CharField(
        source='term.name',
        read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'student', 'student_name', 'student_admission_number',
            'classroom', 'classroom_name', 'term', 'term_name',
            'issue_date', 'due_date', 'total_amount', 'amount_paid',
            'balance', 'status', 'created_at'
        ]
        read_only_fields = [
            'issue_date', 'amount_paid', 'status', 'balance',
            'student_name', 'student_admission_number', 'classroom_name',
            'term_name', 'created_at'
        ]