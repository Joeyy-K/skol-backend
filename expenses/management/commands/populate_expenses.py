import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from expenses.models import Expense, ExpenseCategory

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with realistic expense data for testing.'

    # Defines an optional command-line argument, e.g., --count 200
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=150,
            help='The number of random expenses to create.'
        )

    @transaction.atomic # Ensures all database operations are done in one go
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting expense data population..."))

        count = options['count']

        # --- Cleanup: Delete old data to start fresh ---
        self.stdout.write("Deleting old expense data...")
        Expense.objects.all().delete()
        ExpenseCategory.objects.all().delete()

        # --- Find an admin user to assign as 'recorded_by' ---
        admin_user = User.objects.filter(role='ADMIN').first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No ADMIN user found. Please create an admin user first."))
            return

        # --- Create Expense Categories ---
        self.stdout.write("Creating expense categories...")
        category_names = [
            "Salaries & Wages", "Utilities", "Maintenance & Repairs", 
            "Office Supplies", "Educational Materials", "Transport", 
            "Marketing & Events", "Rent & Lease", "Technology & Software"
        ]
        categories = {name: ExpenseCategory.objects.create(name=name) for name in category_names}
        self.stdout.write(f"{len(categories)} categories created.")

        # --- Prepare Realistic Sample Data ---
        expense_templates = {
            "Salaries & Wages": ["Monthly Staff Payroll", "Teacher Bonuses", "Admin Staff Salaries"],
            "Utilities": ["KPLC Electricity Bill", "NCWSC Water Bill", "Safaricom Internet Bill"],
            "Maintenance & Repairs": ["Classroom A window repair", "Plumbing services for washrooms", "Generator fuel and service"],
            "Office Supplies": ["A4 Reams and Printer Ink", "Purchase of Staplers and Pens", "Whiteboard Markers"],
            "Educational Materials": ["New Chemistry Lab Equipment", "Library Book Purchase", "Grade 5 Textbooks Order"],
            "Transport": ["School Bus Fuel for the Week", "Bus #3 Tyre Replacement", "Driver's weekly allowance"],
            "Marketing & Events": ["Social Media Ad Campaign", "Annual Sports Day Catering", "Printing of new brochures"],
            "Rent & Lease": ["Monthly Campus Rent Payment", "Lease for additional playground"],
            "Technology & Software": ["Zoom Subscription Renewal", "School Management System License", "New Laptops for Staff"],
        }
        
        # --- Generate and Create Expenses in Bulk ---
        self.stdout.write(f"Generating {count} random expenses...")
        expenses_to_create = []
        today = date.today()

        for i in range(count):
            # Pick a random category and a random description for it
            category_name = random.choice(list(expense_templates.keys()))
            category_obj = categories[category_name]
            description = random.choice(expense_templates[category_name])

            # Generate a random date within the last 365 days
            expense_date = today - timedelta(days=random.randint(0, 365))
            
            # Generate a random amount
            amount = Decimal(random.uniform(2000, 150000)).quantize(Decimal("0.01"))

            expenses_to_create.append(
                Expense(
                    description=f"{description} (auto-gen #{i+1})",
                    amount=amount,
                    category=category_obj,
                    expense_date=expense_date,
                    recorded_by=admin_user
                )
            )

        # Use bulk_create for high performance - one database query instead of 150!
        Expense.objects.bulk_create(expenses_to_create)

        self.stdout.write(self.style.SUCCESS(f"Successfully populated the database with {count} expenses!"))