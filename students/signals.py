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
    # The 'created' flag is True only on the first save (i.e., object creation)
    if created and instance.role == 'STUDENT':
        # Create a unique, temporary admission number.
        # This should be updated later by an admin.
        admission_number = f"TEMP-{instance.id}-{timezone.now().strftime('%Y%m%d')}"
        
        # Create the StudentProfile with only fields that exist in your model
        StudentProfile.objects.create(
            user=instance,
            admission_number=admission_number,
            date_of_birth=timezone.now().date(),  # Placeholder DOB
            address="Not Specified",  # This field exists in your model
            # classroom=None (will be set to null by default)
        )
        print(f"StudentProfile created for {instance.email}")