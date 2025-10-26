import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from calendar_events.models import Event
from exams.models import Term, Exam
from fees.models import Invoice
from students.models import StudentProfile
from subjects.models import Subject
from classes.models import Class as Classroom

class Command(BaseCommand):
    help = 'Populates the database with a variety of realistic calendar events.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting calendar event population..."))

        # --- Cleanup: Delete old auto-generated data ---
        # We only delete events, not the source objects (Exams, Invoices etc.)
        self.stdout.write("Deleting old calendar events...")
        Event.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Old events cleared."))

        # --- Get existing data to link events to ---
        terms = list(Term.objects.all())
        exams = list(Exam.objects.all())
        invoices = list(Invoice.objects.all())

        if not terms:
            self.stdout.write(self.style.WARNING("No academic terms found. Some events may not be created."))
        if not exams:
            self.stdout.write(self.style.WARNING("No exams found. Exam events will not be created."))
        if not invoices:
            self.stdout.write(self.style.WARNING("No invoices found. Fee deadline events will not be created."))

        # --- Create Events from Existing Data (using signals logic) ---
        self.stdout.write("Generating events from existing Terms, Exams, and Invoices...")
        
        # 1. Academic Term Events
        for term in terms:
            start_time = timezone.make_aware(timezone.datetime.combine(term.start_date, timezone.datetime.min.time()))
            end_time = timezone.make_aware(timezone.datetime.combine(term.end_date, timezone.datetime.max.time()))
            Event.objects.create(
                event_type='ACADEMIC_TERM',
                title=f"Academic Term: {term.display_name}",
                start_time=start_time,
                end_time=end_time,
                description=f"Start of {term.display_name} is {term.start_date} and it ends on {term.end_date}."
            )

        # 2. Exam Events
        for exam in exams:
            start_time = timezone.make_aware(timezone.datetime.combine(exam.date, timezone.datetime.min.time()))
            end_time = timezone.make_aware(timezone.datetime.combine(exam.date, timezone.datetime.max.time()))
            Event.objects.create(
                event_type='EXAM',
                title=f"Exam: {exam.name} ({exam.subject.name})",
                start_time=start_time,
                end_time=end_time,
                description=f"Exam for {exam.classroom.name} on subject {exam.subject.name}."
            )

        # 3. Fee Deadline Events
        for invoice in invoices:
            start_time = timezone.make_aware(timezone.datetime.combine(invoice.due_date, timezone.datetime.min.time()))
            end_time = timezone.make_aware(timezone.datetime.combine(invoice.due_date, timezone.datetime.max.time()))
            Event.objects.create(
                event_type='FEE_DEADLINE',
                title=f"Fee Deadline: Invoice #{invoice.id}",
                start_time=start_time,
                end_time=end_time,
                description=f"Payment of {invoice.total_amount} is due for {invoice.student.user.full_name}."
            )
        
        self.stdout.write(self.style.SUCCESS("Events created from existing data."))

        # --- Create New, Unique School Events & Holidays ---
        self.stdout.write("Generating new, unique school events and holidays...")
        today = timezone.now()
        
        school_events = [
            {'title': 'Annual Sports Day', 'offset': 45, 'type': 'SCHOOL_EVENT', 'desc': 'All students participate in various sports activities.'},
            {'title': 'Parent-Teacher Conference', 'offset': 60, 'type': 'SCHOOL_EVENT', 'desc': 'Parents meet with teachers to discuss student progress.'},
            {'title': 'Science Fair', 'offset': 75, 'type': 'SCHOOL_EVENT', 'desc': 'Exhibition of student science projects.'},
            {'title': 'Mid-Term Break', 'offset': 90, 'type': 'HOLIDAY', 'desc': 'School closed for mid-term break.'},
            {'title': 'Graduation Ceremony', 'offset': 120, 'type': 'SCHOOL_EVENT', 'desc': 'Ceremony for the graduating class.'},
            {'title': 'Christmas Break', 'offset': 150, 'type': 'HOLIDAY', 'desc': 'School closed for the Christmas holidays.'}
        ]

        for event_data in school_events:
            event_date = today + timedelta(days=event_data['offset'])
            start_time = timezone.make_aware(timezone.datetime.combine(event_date.date(), timezone.datetime.min.time()))
            end_time = timezone.make_aware(timezone.datetime.combine(event_date.date(), timezone.datetime.max.time()))
            
            Event.objects.create(
                title=event_data['title'],
                start_time=start_time,
                end_time=end_time,
                event_type=event_data['type'],
                description=event_data['desc']
            )

        self.stdout.write(self.style.SUCCESS("Unique events and holidays created."))
        self.stdout.write(self.style.SUCCESS("Calendar population complete!"))
