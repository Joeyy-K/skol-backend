from django.core.management.base import BaseCommand
from django.utils import timezone
from auth_system.models import User
from teachers.models import TeacherProfile

class Command(BaseCommand):
    help = 'Finds users with the TEACHER role who are missing a TeacherProfile and creates one for them.'

    def handle(self, *args, **options):
        # Find all users with role 'TEACHER' that do NOT have a linked teacher_profile.
        # The `teacher_profile__isnull=True` finds users where the reverse relationship is NULL.
        missing_profile_users = User.objects.filter(role='TEACHER', teacher_profile__isnull=True)

        if not missing_profile_users.exists():
            self.stdout.write(self.style.SUCCESS('All teacher users already have a profile. Nothing to do.'))
            return

        self.stdout.write(f'Found {missing_profile_users.count()} teacher users missing a profile. Creating now...')

        count = 0
        for user in missing_profile_users:
            # Create a unique, temporary employee ID
            employee_id = f"TEMP-{user.id}-{timezone.now().strftime('%Y%m%d')}"

            # Create the TeacherProfile with placeholder data
            TeacherProfile.objects.create(
                user=user,
                employee_id=employee_id,
                specialization="Not Specified",
                date_of_hire=timezone.now().date()  # Placeholder
            )
            count += 1
            self.stdout.write(self.style.SUCCESS(f'Successfully created profile for teacher: {user.email}'))
        
        self.stdout.write(self.style.WARNING(f'Finished! Created {count} missing teacher profiles.'))