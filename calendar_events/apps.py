from django.apps import AppConfig

class CalendarEventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calendar_events'

    def ready(self):
        import calendar_events.signals 