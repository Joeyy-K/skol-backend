from django.core.management.base import BaseCommand
from django.urls import get_resolver

class Command(BaseCommand):
    help = "Displays all URL patterns in the project"

    def handle(self, *args, **kwargs):
        urls = get_resolver().url_patterns
        self.print_urls(urls)

    def print_urls(self, urlpatterns, prefix=''):
        for pattern in urlpatterns:
            if hasattr(pattern, 'url_patterns'):
                self.print_urls(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                self.stdout.write(prefix + str(pattern.pattern))
