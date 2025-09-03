from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from students.models import StudentProfile

# It's better to import the User model directly from the auth_system app
from auth_system.models import User

class Command(BaseCommand):
    help = 'Finds users with the STUDENT role who are missing a StudentProfile and creates one for them.'

    def handle(self, *args, **options):
        # Find all users with role 'STUDENT' that do NOT have a linked student_profile.
        # The `student_profile__isnull=True` is the key to finding the missing ones.
        missing_profile_users = User.objects.filter(role='STUDENT', student_profile__isnull=True)

        if not missing_profile_users.exists():
            self.stdout.write(self.style.SUCCESS('All student users already have a profile. Nothing to do.'))
            return

        self.stdout.write(f'Found {missing_profile_users.count()} student users missing a profile. Creating now...')

        count = 0
        for user in missing_profile_users:
            # Create a unique, temporary admission number.
            admission_number = f"TEMP-{user.id}-{timezone.now().strftime('%Y%m%d')}"

            # Create the StudentProfile with placeholder data
            StudentProfile.objects.create(
                user=user,
                admission_number=admission_number,
                classroom_id="Unassigned",
                date_of_birth=timezone.now().date(),  # Placeholder
                guardian_name="Not Specified",
                guardian_contact="Not Specified",
                address="Not Specified"
            )
            count += 1
            self.stdout.write(self.style.SUCCESS(f'Successfully created profile for {user.email}'))
        
        self.stdout.write(self.style.WARNING(f'Finished! Created {count} missing student profiles.'))