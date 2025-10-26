from django.db.models.signals import post_save, post_delete # 
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime, time

from exams.models import Exam, Term
from fees.models import Invoice
from .models import Event

from exams.models import Exam, Term
from fees.models import Invoice
from schedules.models import ScheduleEntry 
from .models import Event

@receiver(post_save, sender=Term)
def create_or_update_term_event(sender, instance, created, **kwargs):
    """
    Creates or updates a calendar Event when a Term is saved.
    """
    start_time = timezone.make_aware(timezone.datetime.combine(instance.start_date, timezone.datetime.min.time()))
    end_time = timezone.make_aware(timezone.datetime.combine(instance.end_date, timezone.datetime.max.time()))

    Event.objects.update_or_create(
        event_type='ACADEMIC_TERM',
        title=f"Academic Term: {instance.display_name}",
        defaults={
            'start_time': start_time,
            'end_time': end_time,
            'description': f"Start of {instance.display_name} is {instance.start_date} and it ends on {instance.end_date}."
        }
    )

@receiver(post_save, sender=Exam)
def create_or_update_exam_event(sender, instance, created, **kwargs):
    """
    Creates or updates a calendar Event when an Exam is saved.
    """
    start_time = timezone.make_aware(timezone.datetime.combine(instance.date, timezone.datetime.min.time()))
    end_time = timezone.make_aware(timezone.datetime.combine(instance.date, timezone.datetime.max.time()))

    Event.objects.update_or_create(
        event_type='EXAM',
        title=f"Exam: {instance.name} ({instance.subject.name})",
        group_id=f"exam-{instance.id}",
        defaults={ ... }
    )

@receiver(post_save, sender=Invoice)
def create_or_update_invoice_event(sender, instance, created, **kwargs):
    """
    Creates or updates a calendar Event for an Invoice due date.
    """
    start_time = timezone.make_aware(timezone.datetime.combine(instance.due_date, timezone.datetime.min.time()))
    end_time = timezone.make_aware(timezone.datetime.combine(instance.due_date, timezone.datetime.max.time()))

    Event.objects.update_or_create(
        event_type='FEE_DEADLINE',
        title=f"Fee Deadline: Invoice #{instance.id}",
        group_id=f"invoice-{instance.id}", 
        defaults={
            'start_time': start_time,
            'end_time': end_time,
            'description': f"Payment of {instance.total_amount} is due for {instance.student.user.full_name}."
        }
    )

def get_next_weekday(start_date, weekday_int):
    days_ahead = weekday_int - start_date.weekday()
    if days_ahead < 0: 
        days_ahead += 7
    return start_date + timezone.timedelta(days=days_ahead)

@receiver(post_save, sender=ScheduleEntry)
def create_or_update_schedule_event(sender, instance, created, **kwargs):
    """
    Creates or updates a recurring calendar Event when a ScheduleEntry is saved.
    This is complex because a schedule entry is weekly, but calendar events are specific dates.
    
    We'll create events for the duration of the entry's academic term.
    """
    term = instance.term
    if not term:
        return 

    weekday_map = {
        'MONDAY': 0, 'TUESDAY': 1, 'WEDNESDAY': 2, 'THURSDAY': 3,
        'FRIDAY': 4, 'SATURDAY': 5, 'SUNDAY': 6
    }
    target_weekday = weekday_map.get(instance.day_of_week)

    if target_weekday is None:
        return

    current_date = get_next_weekday(term.start_date, target_weekday)

    group_id = f"schedule-{instance.id}"
    
    Event.objects.filter(group_id=group_id).delete()

    events_to_create = []
    while current_date <= term.end_date:
        start_time = timezone.make_aware(datetime.combine(current_date, instance.timeslot.start_time))
        end_time = timezone.make_aware(datetime.combine(current_date, instance.timeslot.end_time))

        events_to_create.append(
            Event(
                title=f"{instance.subject.name} - {instance.classroom.name}",
                start_time=start_time,
                end_time=end_time,
                event_type='CLASS_SCHEDULE',
                description=f"Taught by {instance.teacher.full_name}",
                group_id=group_id,
            )
        )
        current_date += timezone.timedelta(weeks=1)

    Event.objects.bulk_create(events_to_create)

@receiver(post_delete, sender=ScheduleEntry)
def delete_schedule_event(sender, instance, **kwargs):
    """
    Deletes all associated recurring calendar events when a ScheduleEntry is deleted.
    """
    group_id = f"schedule-{instance.id}"
    Event.objects.filter(group_id=group_id).delete()