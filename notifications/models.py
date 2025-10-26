from django.db import models
from django.conf import settings

class Notification(models.Model):
    """
    Stores a single notification for a specific user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.TextField(
        help_text="The content of the notification."
    )
    is_read = models.BooleanField(
        default=False, 
        db_index=True
    )
    link = models.URLField(
        max_length=500, 
        blank=True, 
        null=True
    )
    timestamp = models.DateTimeField(
        auto_now_add=True, 
        db_index=True
    )

    class Meta:
        ordering = ['-timestamp'] # Show newest notifications first

    def __str__(self):
        return f"Notification for {self.user.email}: {self.message[:30]}..."