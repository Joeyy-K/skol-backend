from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import ParentProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_parent_profile(sender, instance, created, **kwargs):
    """
    Automatically create a ParentProfile when a User with role 'PARENT' is created.
    """
    if created and instance.role == 'PARENT':
        ParentProfile.objects.create(user=instance)
        print(f"ParentProfile created for {instance.email}")