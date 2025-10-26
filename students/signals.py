from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from .models import StudentProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_student_profile(sender, instance, created, **kwargs):
    """
    Automatically create a StudentProfile when a User with role 'STUDENT' is created.
    """
    if created and instance.role == 'STUDENT' and not instance.is_superuser and not instance.is_staff:
        admission_number = f"TEMP-{instance.id}-{timezone.now().strftime('%Y%m%d')}"
        
        StudentProfile.objects.create(
            user=instance,
            admission_number=admission_number,
            date_of_birth=timezone.now().date(), 
            address="Not Specified",  
        )
        print(f"StudentProfile created for {instance.email}")