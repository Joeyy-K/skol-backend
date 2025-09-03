import random
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from tqdm import tqdm

# Import required models
from auth_system.models import User
from students.models import StudentProfile
from classes.models import Class
from exams.models import Term
from fees.models import FeeStructure, Invoice, InvoiceItem, Payment

fake = Faker()


class Command(BaseCommand):
    help = 'Populate the school ERP database with realistic financial data (fees, invoices, payments)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--invoices_percentage',
            type=int,
            default=80,
            help='Percentage of students for whom invoices should be generated (default: 80)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('This will populate the database with financial data.')
        )
        self.stdout.write(
            self.style.WARNING(f"Invoice percentage: {options['invoices_percentage']}%")
        )

        # Confirmation prompt
        if not options['force']:
            confirm = input('\nThis will DELETE existing financial data. Continue? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Start the population process
        self.stdout.write(self.style.SUCCESS('\nStarting financial data population...'))
        
        try:
            # Step 1: Validate prerequisites
            self.validate_prerequisites()
            
            # Step 2: Wipe existing financial data
            self.wipe_financial_data()
            
            # Step 3: Create fee structures
            active_term = self.create_fee_structures()
            
            # Step 4: Generate invoices and invoice items
            invoices = self.generate_invoices_and_items(active_term, options['invoices_percentage'])
            
            # Step 5: Generate payments
            self.generate_payments(invoices)
            
            self.stdout.write(
                self.style.SUCCESS('\n✅ Financial data population completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error during population: {str(e)}')
            )
            raise

    def validate_prerequisites(self):
        """Validate that required data exists in the database"""
        self.stdout.write('🔍 Validating prerequisites...')
        
        # Check for active term
        try:
            active_term = Term.objects.get(is_active=True)
            self.stdout.write(f'  Found active term: {active_term.name}')
        except Term.DoesNotExist:
            raise Exception('No active term found. Please ensure there is an active term in the database.')
        except Term.MultipleObjectsReturned:
            raise Exception('Multiple active terms found. Please ensure only one term is marked as active.')
        
        # Check for classes
        classes_count = Class.objects.count()
        if classes_count == 0:
            raise Exception('No classes found in the database. Please run populate_db first.')
        self.stdout.write(f'  Found {classes_count} classes')
        
        # Check for students
        students_count = StudentProfile.objects.count()
        if students_count == 0:
            raise Exception('No students found in the database. Please run populate_db first.')
        self.stdout.write(f'  Found {students_count} students')
        
        # Check for superuser (for payment recorded_by field)
        superuser_count = User.objects.filter(is_superuser=True).count()
        if superuser_count == 0:
            self.stdout.write(self.style.WARNING('  No superuser found. Payments will be recorded without a user.'))
        else:
            self.stdout.write(f'  Found {superuser_count} superuser(s)')
        
        self.stdout.write(self.style.SUCCESS('✅ Prerequisites validated'))

    @transaction.atomic
    def wipe_financial_data(self):
        """Delete all existing financial data"""
        self.stdout.write('🗑️  Wiping existing financial data...')
        
        # Delete in correct order to respect foreign key constraints
        financial_models = [
            Payment,
            InvoiceItem,
            Invoice,
            FeeStructure,
        ]
        
        total_deleted = 0
        for model in financial_models:
            count = model.objects.count()
            model.objects.all().delete()
            total_deleted += count
            self.stdout.write(f'  Deleted {count} {model.__name__} records')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Financial data wipe completed - {total_deleted} records deleted'))

    @transaction.atomic
    def create_fee_structures(self):
        """Create fee structures for all classes in the active term"""
        self.stdout.write('\n💰 Creating fee structures...')
        
        # Get active term
        active_term = Term.objects.get(is_active=True)
        classes = list(Class.objects.all())
        
        # Define fee types with realistic amounts
        fee_types = [
            {'name': 'Tuition Fee', 'description': 'Term tuition fee', 'min_amount': 15000, 'max_amount': 25000},
            {'name': 'Bus Transportation Fee', 'description': 'School bus transportation', 'min_amount': 3000, 'max_amount': 5000},
            {'name': 'Activity Fee', 'description': 'Co-curricular activities fee', 'min_amount': 1000, 'max_amount': 2500},
            {'name': 'Library Fee', 'description': 'Library services and books', 'min_amount': 500, 'max_amount': 1500},
            {'name': 'Laboratory Fee', 'description': 'Science laboratory usage', 'min_amount': 2000, 'max_amount': 4000},
            {'name': 'Sports Fee', 'description': 'Sports equipment and facilities', 'min_amount': 800, 'max_amount': 1800},
        ]
        
        fee_structures_to_create = []
        
        for class_obj in tqdm(classes, desc="Creating fee structures"):
            # Each class gets 3-5 random fee types
            selected_fees = random.sample(fee_types, random.randint(3, 5))
            
            for fee_type in selected_fees:
                amount = Decimal(str(random.randint(fee_type['min_amount'], fee_type['max_amount'])))
                
                fee_structures_to_create.append(FeeStructure(
                    name=fee_type['name'],
                    description=fee_type['description'],
                    amount=amount,
                    classroom=class_obj,
                    term=active_term
                ))
        
        # Bulk create fee structures
        FeeStructure.objects.bulk_create(fee_structures_to_create, batch_size=100)
        
        self.stdout.write(f'  Created {len(fee_structures_to_create)} fee structures')
        self.stdout.write(self.style.SUCCESS('✅ Fee structures created'))
        
        return active_term

    @transaction.atomic
    def generate_invoices_and_items(self, active_term, invoices_percentage):
        """Generate invoices and invoice items for selected students"""
        self.stdout.write(f'\n🧾 Generating invoices for {invoices_percentage}% of students...')
        
        # Get all students and select the specified percentage
        all_students = list(StudentProfile.objects.select_related('user', 'classroom').all())
        num_students_for_invoices = int(len(all_students) * invoices_percentage / 100)
        selected_students = random.sample(all_students, num_students_for_invoices)
        
        self.stdout.write(f'  Selected {len(selected_students)} students out of {len(all_students)}')
        
        invoices_to_create = []
        invoice_items_to_create = []
        
        # Calculate due date (30 days from today)
        due_date = date.today() + timedelta(days=30)
        
        for student in tqdm(selected_students, desc="Creating invoices"):
            # Get fee structures for this student's class
            fee_structures = list(FeeStructure.objects.filter(
                classroom=student.classroom,
                term=active_term
            ))
            
            if not fee_structures:
                continue  # Skip if no fee structures for this class
            
            # Calculate total amount
            total_amount = sum(fs.amount for fs in fee_structures)
            
            # Create invoice
            invoice = Invoice(
                student=student,
                classroom=student.classroom,
                term=active_term,
                due_date=due_date,
                total_amount=total_amount,
                amount_paid=Decimal('0.00'),
                status='UNPAID'
            )
            invoices_to_create.append(invoice)
            
            # Prepare invoice items (we'll create them after invoices are saved)
            for fee_structure in fee_structures:
                invoice_items_to_create.append({
                    'invoice_index': len(invoices_to_create) - 1,  # Reference to invoice
                    'description': f'{fee_structure.name} - {active_term.name}',
                    'amount': fee_structure.amount
                })
        
        # Bulk create invoices
        created_invoices = Invoice.objects.bulk_create(invoices_to_create, batch_size=100)
        self.stdout.write(f'  Created {len(created_invoices)} invoices')
        
        # Now create invoice items with proper invoice references
        actual_invoice_items = []
        for item_data in tqdm(invoice_items_to_create, desc="Creating invoice items"):
            invoice = created_invoices[item_data['invoice_index']]
            actual_invoice_items.append(InvoiceItem(
                invoice=invoice,
                description=item_data['description'],
                amount=item_data['amount']
            ))
        
        InvoiceItem.objects.bulk_create(actual_invoice_items, batch_size=200)
        self.stdout.write(f'  Created {len(actual_invoice_items)} invoice items')
        
        self.stdout.write(self.style.SUCCESS('✅ Invoices and invoice items generated'))
        
        return created_invoices

    @transaction.atomic
    def generate_payments(self, invoices):
        """Generate payment records for approximately 50% of invoices"""
        self.stdout.write('\n💳 Generating payments...')
        
        # Get superuser for recorded_by field
        try:
            superuser = User.objects.filter(is_superuser=True).first()
        except User.DoesNotExist:
            superuser = None
        
        # Select about 50% of invoices for payments
        num_invoices_with_payments = int(len(invoices) * 0.5)
        invoices_for_payments = random.sample(invoices, num_invoices_with_payments)
        
        payment_methods = ['CASH', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE']
        payments_to_create = []
        
        for invoice in tqdm(invoices_for_payments, desc="Creating payments"):
            # Decide payment scenario: full payment (70%) or partial payment (30%)
            if random.random() < 0.7:
                # Full payment
                payment_amount = invoice.total_amount
                payments_to_create.append(self._create_payment_data(
                    invoice, payment_amount, superuser, payment_methods
                ))
            else:
                # Partial payments (1-2 payments)
                remaining_amount = invoice.total_amount
                num_payments = random.randint(1, 2)
                
                for i in range(num_payments):
                    if i == num_payments - 1:
                        # Last payment gets the remaining amount
                        payment_amount = remaining_amount
                    else:
                        # Random partial amount (30-70% of remaining)
                        payment_percentage = random.uniform(0.3, 0.7)
                        payment_amount = remaining_amount * Decimal(str(payment_percentage))
                        payment_amount = payment_amount.quantize(Decimal('0.01'))
                        remaining_amount -= payment_amount
                    
                    if payment_amount > 0:
                        payments_to_create.append(self._create_payment_data(
                            invoice, payment_amount, superuser, payment_methods
                        ))
        
        # Bulk create payments
        Payment.objects.bulk_create(payments_to_create, batch_size=100)
        
        # Update invoice statuses and amounts_paid
        self._update_invoice_statuses(invoices_for_payments)
        
        self.stdout.write(f'  Created {len(payments_to_create)} payments')
        self.stdout.write(f'  Updated payment status for {len(invoices_for_payments)} invoices')
        self.stdout.write(self.style.SUCCESS('✅ Payments generated'))

    def _create_payment_data(self, invoice, amount, recorded_by, payment_methods):
        """Helper method to create payment data"""
        return Payment(
            invoice=invoice,
            amount=amount,
            payment_date=fake.date_between(
                start_date=invoice.issue_date,
                end_date=date.today()
            ),
            payment_method=random.choice(payment_methods),
            reference_code=f'REF{random.randint(100000, 999999)}' if random.random() < 0.7 else '',
            recorded_by=recorded_by,
            notes=fake.sentence() if random.random() < 0.3 else ''
        )

    def _update_invoice_statuses(self, invoices):
        """Update invoice payment amounts and statuses after payments are created"""
        for invoice in tqdm(invoices, desc="Updating invoice statuses"):
            # Calculate total payments for this invoice
            total_payments = sum(
                payment.amount for payment in Payment.objects.filter(invoice=invoice)
            )
            
            # Update invoice
            invoice.amount_paid = total_payments
            invoice.update_status()
            invoice.save()

    def get_summary_stats(self):
        """Print summary statistics after population"""
        self.stdout.write('\n📊 Summary Statistics:')
        
        fee_structures_count = FeeStructure.objects.count()
        invoices_count = Invoice.objects.count()
        invoice_items_count = InvoiceItem.objects.count()
        payments_count = Payment.objects.count()
        
        paid_invoices = Invoice.objects.filter(status='PAID').count()
        partially_paid_invoices = Invoice.objects.filter(status='PARTIALLY_PAID').count()
        unpaid_invoices = Invoice.objects.filter(status='UNPAID').count()
        
        total_invoice_amount = sum(
            invoice.total_amount for invoice in Invoice.objects.all()
        )
        total_payments_amount = sum(
            payment.amount for payment in Payment.objects.all()
        )
        
        self.stdout.write(f'  Fee Structures: {fee_structures_count}')
        self.stdout.write(f'  Invoices: {invoices_count}')
        self.stdout.write(f'  Invoice Items: {invoice_items_count}')
        self.stdout.write(f'  Payments: {payments_count}')
        self.stdout.write(f'  Paid Invoices: {paid_invoices}')
        self.stdout.write(f'  Partially Paid Invoices: {partially_paid_invoices}')
        self.stdout.write(f'  Unpaid Invoices: {unpaid_invoices}')
        self.stdout.write(f'  Total Invoice Amount: KES {total_invoice_amount:,.2f}')
        self.stdout.write(f'  Total Payments Amount: KES {total_payments_amount:,.2f}')
        self.stdout.write(f'  Outstanding Balance: KES {total_invoice_amount - total_payments_amount:,.2f}')