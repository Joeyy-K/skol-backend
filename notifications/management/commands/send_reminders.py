from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from calendar_events.models import Event
from notifications.models import Notification
from fees.models import Invoice
from exams.models import Exam

User = get_user_model()

class Command(BaseCommand):
    help = 'Scans for upcoming events and generates notifications for relevant users.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting notification generation..."))
        
        now = timezone.now()
        tomorrow = now.date() + timedelta(days=1)
        in_3_days = now.date() + timedelta(days=3)

        # --- Find upcoming events ---
        upcoming_events = Event.objects.filter(
            start_time__date__in=[tomorrow, in_3_days],
        ).exclude(event_type='CLASS_SCHEDULE') # We don't need reminders for every class

        if not upcoming_events.exists():
            self.stdout.write("No upcoming events to notify for. Exiting.")
            return

        for event in upcoming_events:
            days_away = (event.start_time.date() - now.date()).days
            
            if days_away == 1:
                time_adverb = "tomorrow"
            else:
                time_adverb = f"in {days_away} days"

            message = f"Reminder: {event.title} is {time_adverb}."
            link = None # We can set specific links later

            # --- Determine who to notify ---
            users_to_notify = []

            if event.event_type == 'EXAM':
                # Notify all students in the exam's classroom
                exam_id = event.group_id.split('-')[1] # Assumes group_id is 'exam-123'
                exam = Exam.objects.get(id=exam_id)
                students = exam.classroom.students.all()
                users_to_notify.extend([s.user for s in students])
                link = f"/exams/{exam.id}" # Link to the exam detail page
            
            elif event.event_type == 'FEE_DEADLINE':
                # This is a summary event, so we need to find all related invoices
                invoices = Invoice.objects.filter(due_date=event.start_time.date())
                for invoice in invoices:
                    parents = invoice.student.parents.all()
                    users_to_notify.extend([p.user for p in parents])
                link = "/my-billing" # Link to parent's billing page

            elif event.event_type in ['HOLIDAY', 'SCHOOL_EVENT']:
                # Notify all active users
                users_to_notify = User.objects.filter(is_active=True)
                link = "/calendar"

            # Create notifications, avoiding duplicates
            for user in set(users_to_notify):
                Notification.objects.get_or_create(
                    user=user,
                    message=message,
                    defaults={'link': link}
                )
        
        self.stdout.write(self.style.SUCCESS(f"Processed {upcoming_events.count()} events. Notifications created."))
