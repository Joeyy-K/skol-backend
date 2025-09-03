from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone

from .models import TeacherProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_teacher_profile(sender, instance, created, **kwargs):
    """
    Automatically create a TeacherProfile when a User with role 'TEACHER' is created.
    """
    if created and instance.role == 'TEACHER':
        if not TeacherProfile.objects.filter(user=instance).exists():
            TeacherProfile.objects.create(
                user=instance,
                employee_id=f"TEMP-{instance.id}-{timezone.now().strftime('%Y%m%d')}",
                specialization="Not Assigned",
                date_of_hire=timezone.now().date()
            )
            print(f"TeacherProfile created for {instance.email}")