from django.core.management.base import BaseCommand
from auth_system.models import User
from parents.models import ParentProfile

class Command(BaseCommand):
    help = 'Creates ParentProfile for users with the PARENT role who are missing one.'

    def handle(self, *args, **options):
        missing_profile_users = User.objects.filter(role='PARENT', parent_profile__isnull=True)

        if not missing_profile_users.exists():
            self.stdout.write(self.style.SUCCESS('All parent users already have a profile.'))
            return

        self.stdout.write(f'Found {missing_profile_users.count()} parent users missing a profile. Creating now...')

        count = 0
        for user in missing_profile_users:
            ParentProfile.objects.create(user=user)
            count += 1
            self.stdout.write(self.style.SUCCESS(f'Successfully created profile for parent: {user.email}'))
        
        self.stdout.write(self.style.WARNING(f'Finished! Created {count} missing parent profiles.'))