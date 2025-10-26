import random
from datetime import datetime, timedelta, date
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from faker import Faker
from tqdm import tqdm

# Import all required models
from auth_system.models import User
from students.models import StudentProfile
from teachers.models import TeacherProfile
from parents.models import ParentProfile
from classes.models import Class
from subjects.models import Subject
from exams.models import Term, Exam, StudentScore
from attendance.models import AttendanceRecord
from schedules.models import TimeSlot, ScheduleEntry

fake = Faker()


class Command(BaseCommand):
    help = 'Populate the school ERP database with realistic fake data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--students',
            type=int,
            default=200,
            help='Number of students to create (default: 200)'
        )
        parser.add_argument(
            '--teachers',
            type=int,
            default=20,
            help='Number of teachers to create (default: 20)'
        )
        parser.add_argument(
            '--classes',
            type=int,
            default=15,
            help='Number of classes to create (default: 15)'
        )
        parser.add_argument(
            '--subjects',
            type=int,
            default=10,
            help='Number of subjects to create (default: 10)'
        )
        parser.add_argument(
            '--parents',
            type=int,
            default=150,
            help='Number of parents to create (default: 150)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('This will populate the database with fake data.')
        )
        self.stdout.write(
            self.style.WARNING(f"Students: {options['students']}")
        )
        self.stdout.write(
            self.style.WARNING(f"Teachers: {options['teachers']}")
        )
        self.stdout.write(
            self.style.WARNING(f"Classes: {options['classes']}")
        )
        self.stdout.write(
            self.style.WARNING(f"Subjects: {options['subjects']}")
        )
        self.stdout.write(
            self.style.WARNING(f"Parents: {options['parents']}")
        )

        # Confirmation prompt
        if not options['force']:
            confirm = input('\nThis will DELETE existing data. Continue? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Start the population process
        self.stdout.write(self.style.SUCCESS('\nStarting database population...'))
        
        # Step 1: Wipe existing data
        self.wipe_existing_data()
        
        # Step 2: Create academic structure
        terms = self.create_academic_structure(options)
        
        # Step 3: Create users and profiles
        users_data = self.create_users_and_profiles(options)
        
        # Step 4: Create relationships
        self.create_relationships(users_data, options)
        
        # Step 5: Generate records
        self.generate_records(users_data, terms, options)
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Database population completed successfully!')
        )

    def wipe_existing_data(self):
        """Delete all existing school data except superusers"""
        self.stdout.write('🗑️  Wiping existing data...')
        
        # Disable foreign key constraints temporarily for SQLite
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute('PRAGMA foreign_keys = OFF;')
        
        try:
            with transaction.atomic():
                # Delete all records in the correct order (children first, then parents)
                models_to_clear = [
                    (AttendanceRecord, 'AttendanceRecord'),
                    (StudentScore, 'StudentScore'), 
                    (Exam, 'Exam'),
                    (ScheduleEntry, 'ScheduleEntry'),
                    (StudentProfile, 'StudentProfile'),
                    (TeacherProfile, 'TeacherProfile'),
                    (ParentProfile, 'ParentProfile'),
                    (Class, 'Class'),
                    (Subject, 'Subject'),
                    (Term, 'Term'),
                    (TimeSlot, 'TimeSlot'),
                ]
                
                for model, name in models_to_clear:
                    count = model.objects.count()
                    if count > 0:
                        # Clear many-to-many relationships first
                        if hasattr(model, '_meta'):
                            for field in model._meta.get_fields():
                                if field.many_to_many:
                                    for obj in model.objects.all():
                                        getattr(obj, field.name).clear()
                        
                        # Delete the records
                        model.objects.all().delete()
                        self.stdout.write(f'  Deleted {count} {name} records')
                
                # Delete non-superuser users
                non_superusers = User.objects.filter(is_superuser=False)
                count = non_superusers.count()
                if count > 0:
                    non_superusers.delete()
                    self.stdout.write(f'  Deleted {count} non-superuser accounts')
                
        finally:
            # Re-enable foreign key constraints
            with connection.cursor() as cursor:
                if connection.vendor == 'sqlite':
                    cursor.execute('PRAGMA foreign_keys = ON;')
        
        self.stdout.write(self.style.SUCCESS('✅ Data wipe completed'))

    def create_academic_structure(self, options):
        """Create terms, classes, subjects, and time slots"""
        self.stdout.write('\n🏫 Creating academic structure...')
        
        current_year = date.today().year
        
        # Create Terms for current year with academic_year field
        terms_data = [
            {'name': 'TERM_1', 'academic_year': current_year, 'start_date': date(current_year, 1, 15), 'end_date': date(current_year, 4, 15), 'is_active': False},
            {'name': 'TERM_2', 'academic_year': current_year, 'start_date': date(current_year, 5, 15), 'end_date': date(current_year, 8, 15), 'is_active': True},
            {'name': 'TERM_3', 'academic_year': current_year, 'start_date': date(current_year, 9, 15), 'end_date': date(current_year, 11, 30), 'is_active': False},
        ]
        
        terms = []
        for data in terms_data:
            term = Term.objects.create(**data)
            terms.append(term)
        
        self.stdout.write(f'  Created {len(terms)} terms for the year {current_year}')
        
        # Create Classes
        class_names = [f'Grade {g}{l}' for g in range(1, 9) for l in ['A', 'B']]
        classes = []
        
        for i in range(options['classes']):
            class_obj = Class.objects.create(
                name=class_names[i] if i < len(class_names) else f'Class {i+1}',
                level=f'Grade {((i // 2) + 1)}'
            )
            classes.append(class_obj)
        
        self.stdout.write(f'  Created {len(classes)} classes')
        
        # Create Subjects
        subject_names = ['Mathematics', 'English', 'Physics', 'Chemistry', 'Biology', 'History', 'Geography', 'Art', 'Music', 'Physical Education']
        subjects = []
        
        for i in range(options['subjects']):
            subject = Subject.objects.create(
                name=subject_names[i] if i < len(subject_names) else f'Subject {i+1}',
                code=f'SUB{i+1:03d}',
                level=f'Grade {random.randint(1, 8)}'
            )
            subjects.append(subject)
        
        self.stdout.write(f'  Created {len(subjects)} subjects')

        # Create Time Slots
        time_slots_data = [
            ('Period 1', '08:00', '08:45'),
            ('Period 2', '08:45', '09:30'),
            ('Break', '09:30', '09:45'),
            ('Period 3', '09:45', '10:30'),
            ('Period 4', '10:30', '11:15'),
            ('Lunch', '12:00', '13:00'),
            ('Period 5', '13:00', '13:45'),
            ('Period 6', '13:45', '14:30')
        ]
        time_slots = []
        for name, start_time, end_time in time_slots_data:
            time_slot = TimeSlot.objects.create(name=name, start_time=start_time, end_time=end_time)
            time_slots.append(time_slot)
        
        self.stdout.write(f'  Created {len(time_slots)} time slots')

        self.stdout.write(self.style.SUCCESS('✅ Academic structure created'))
        return {
            'terms': terms,
            'classes': classes,
            'subjects': subjects,
            'time_slots': time_slots,
            'active_term': Term.objects.get(is_active=True)
        }

    @transaction.atomic
    def create_users_and_profiles(self, options):
        """Create users and their associated profiles in bulk"""
        self.stdout.write('\n👥 Creating users and profiles...')
        
        # ADD A PLACEHOLDER FOR CREDENTIALS
        credentials_to_log = {}
        
        # Create Users
        users_to_create = []
        roles = ['TEACHER', 'PARENT', 'STUDENT']
        counts = {
            'TEACHER': options['teachers'],
            'PARENT': options['parents'],
            'STUDENT': options['students']
        }
        
        for role in roles:
            for i in range(counts[role]):
                full_name = fake.name()
                email = f'{role.lower()}{i+1}@yourschool.demo'  # Use a consistent domain
                
                # LOG THE FIRST OF EACH TYPE
                if i == 0:  # If this is the first user of this role
                    credentials_to_log[role] = {
                        'email': email,
                        'password': 'password123'
                    }
                
                users_to_create.append(User(
                    email=email,
                    full_name=full_name,
                    role=role
                ))
        
        User.objects.bulk_create(users_to_create, batch_size=100)
        
        # Set passwords for all non-superuser users
        users = User.objects.filter(is_superuser=False)
        for user in tqdm(users, desc="Setting passwords"):
            user.set_password('password123')
            user.save()
        
        # Get users by role
        teachers = User.objects.filter(role='TEACHER')
        parents = User.objects.filter(role='PARENT')
        students = User.objects.filter(role='STUDENT')
        
        # Get subject names for teacher specializations
        subject_names = ['Mathematics', 'English', 'Physics', 'Chemistry', 'Biology', 'History', 'Geography', 'Art', 'Music', 'Physical Education']
        
        # Create profiles in bulk
        teacher_profiles = []
        for t in teachers:
            teacher_profiles.append(TeacherProfile(
                user=t,
                employee_id=f'EMP{t.id:04d}',
                specialization=random.choice(subject_names),
                date_of_hire=fake.date_between(start_date='-10y')
            ))
        TeacherProfile.objects.bulk_create(teacher_profiles, batch_size=100)
        
        parent_profiles = []
        for p in parents:
            parent_profiles.append(ParentProfile(
                user=p,
                phone_number=fake.phone_number()
            ))
        ParentProfile.objects.bulk_create(parent_profiles, batch_size=100)
        
        student_profiles = []
        for s in students:
            student_profiles.append(StudentProfile(
                user=s,
                admission_number=f'STU{s.id:04d}',
                date_of_birth=fake.date_of_birth(minimum_age=5, maximum_age=18)
            ))
        StudentProfile.objects.bulk_create(student_profiles, batch_size=100)

        self.stdout.write(self.style.SUCCESS(f'✅ Created {users.count()} users and profiles'))
        
        # CREATE ADMIN USER IF IT DOESN'T EXIST
        admin_email = 'admin@yourschool.demo'
        admin_password = 'admin123'

        if not User.objects.filter(email=admin_email).exists():
            admin_user = User.objects.create_user(
                email=admin_email,
                password=admin_password,
                full_name='System Administrator'
            )
            # Explicitly set admin properties
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.role = 'ADMIN'  # Set role explicitly to ADMIN, not STUDENT
            admin_user.save()
            self.stdout.write(f'  Created admin user: {admin_email}')
        else:
            # If admin exists, ensure it has correct permissions
            admin_user = User.objects.get(email=admin_email)
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.role = 'ADMIN'  # Ensure role is ADMIN
            admin_user.save()
            self.stdout.write('  Admin user updated with correct permissions')

        # PRINT THE CREDENTIALS AT THE END
        self.stdout.write(self.style.NOTICE('\n' + '='*50))
        self.stdout.write(self.style.NOTICE('     L O G I N   C R E D E N T I A L S     '))
        self.stdout.write(self.style.NOTICE('='*50))
        
        # Show admin credentials first
        self.stdout.write('  🔐 ADMIN (Django Admin Access):')
        self.stdout.write(f'    Email:    {admin_email}')
        self.stdout.write(f'    Password: {admin_password}')
        self.stdout.write(f'    URL:      /admin/')
        self.stdout.write('')
        
        # Show regular user credentials
        for role, creds in credentials_to_log.items():
            self.stdout.write(f'  👤 {role}:')
            self.stdout.write(f'    Email:    {creds["email"]}')
            self.stdout.write(f'    Password: {creds["password"]}')
        self.stdout.write(self.style.NOTICE('='*50 + '\n'))
        
        return {
            'teachers': list(teachers),
            'parents': list(parents),
            'students': list(students)
        }

    @transaction.atomic
    def create_relationships(self, users_data, options):
        """Create relationships between users, classes, and subjects"""
        self.stdout.write('\n🔗 Creating relationships...')
        
        classes = list(Class.objects.all())
        teachers = users_data['teachers']
        students = list(StudentProfile.objects.all())
        parents = list(ParentProfile.objects.all())

        # Assign teachers to classes as class teachers
        for i, class_obj in enumerate(tqdm(classes, desc="Assigning class teachers")):
            class_obj.teacher_in_charge = teachers[i % len(teachers)]
            class_obj.save()

        # Assign students to classes using update() to bypass validation
        for i, student_profile in enumerate(tqdm(students, desc="Assigning students to classes")):
            # Use update() instead of save() to bypass the clean() method validation
            StudentProfile.objects.filter(id=student_profile.id).update(
                classroom=classes[i % len(classes)]
            )

        # Assign parents to students
        for student_profile in tqdm(students, desc="Assigning parents to students"):
            num_parents = random.choice([1, 2])
            if len(parents) >= num_parents:
                assigned_parents = random.sample(parents, num_parents)
                student_profile.parents.set(assigned_parents)

        self.stdout.write(self.style.SUCCESS('✅ Relationships created'))

    @transaction.atomic
    def generate_records(self, users_data, terms, options):
        """Generate schedule, exams, scores, and attendance records"""
        self.stdout.write('\n📊 Generating academic records...')
        
        active_term = Term.objects.get(is_active=True)
        classes = list(Class.objects.all())
        subjects = list(Subject.objects.all())
        time_slots = list(TimeSlot.objects.all())
        
        # Create weekly schedule for each class
        weekdays = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
        schedule_entries = []
        
        for class_obj in tqdm(classes, desc="Creating schedules"):
            for day in weekdays:
                for time_slot in time_slots:
                    # Skip break and lunch periods
                    if "Break" not in time_slot.name and "Lunch" not in time_slot.name:
                        schedule_entries.append(ScheduleEntry(
                            classroom=class_obj,
                            subject=random.choice(subjects),
                            teacher=class_obj.teacher_in_charge,
                            timeslot=time_slot,
                            day_of_week=day,
                            term=active_term
                        ))
        
        ScheduleEntry.objects.bulk_create(schedule_entries, batch_size=500)
        self.stdout.write(f'  Created {len(schedule_entries)} schedule entries')
        
        # Create exams and scores
        exams = []
        for c in classes:
            for s in subjects:
                exam = Exam(
                    name=f'{s.name} Mid-Term',
                    subject=s,
                    classroom=c,
                    term=active_term,
                    date=fake.date_between(start_date=active_term.start_date, end_date=active_term.end_date),
                    max_score=100,
                    created_by=c.teacher_in_charge
                )
                exams.append(exam)
        
        Exam.objects.bulk_create(exams, batch_size=100)
        
        # Create student scores
        scores = []
        for exam in tqdm(Exam.objects.all(), desc="Creating scores"):
            for student in exam.classroom.students.all():
                scores.append(StudentScore(
                    student=student,
                    exam=exam,
                    score=random.randint(40, 99)
                ))
        StudentScore.objects.bulk_create(scores, batch_size=500)
        self.stdout.write(f'  Created {len(exams)} exams and {len(scores)} scores')

        # Create attendance records
        attendance_records = []
        start_date = max(active_term.start_date, date.today() - timedelta(days=30))
        
        # Generate attendance for the last 30 days (or since term start)
        date_range = [start_date + timedelta(days=x) for x in range((date.today() - start_date).days)]
        
        for day in tqdm(date_range, desc="Creating attendance"):
            if day.weekday() < 5:  # Only weekdays
                for student in StudentProfile.objects.all():
                    # 90% chance present, 5% late, 5% absent
                    status = random.choice(['PRESENT'] * 18 + ['LATE', 'ABSENT'])
                    attendance_records.append(AttendanceRecord(
                        student=student,
                        classroom=student.classroom,
                        date=day,
                        status=status
                    ))
        
        AttendanceRecord.objects.bulk_create(attendance_records, batch_size=500)
        self.stdout.write(f'  Created {len(attendance_records)} attendance records')
        self.stdout.write(self.style.SUCCESS('✅ Academic records generated'))