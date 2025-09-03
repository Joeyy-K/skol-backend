from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from subjects.models import Subject

User = get_user_model()

class SubjectIntegrationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com', password='adminpass', role='ADMIN', is_active=True
        )
        self.teacher = User.objects.create_user(
            email='teacher@example.com', password='teachpass', role='TEACHER', is_active=True
        )
        self.subject_data = {
            'name': 'Mathematics',
            'code': 'MATH101',
            'level': 'Grade 1',
            'description': 'Basic math',
            'teacher_in_charge': self.teacher.id
        }
        self.client.force_authenticate(user=self.admin)

    def test_create_subject(self):
        url = reverse('subject-list')
        response = self.client.post(url, self.subject_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Subject.objects.count(), 1)
        self.assertEqual(Subject.objects.first().name, 'Mathematics')

    def test_list_subjects(self):
        Subject.objects.create(name='English', code='ENG101', level='Grade 1')
        url = reverse('subject-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1) 
        self.assertEqual(len(response.data['results']), 1)

    def test_subject_detail(self):
        subject = Subject.objects.create(
            name='Physics',
            code='PHYS101',
            level='Grade 10',
            teacher_in_charge=self.teacher  # not self.teacher.id
        )
        url = reverse('subject-detail', args=[subject.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Physics')

    def test_assign_teacher(self):
        subject = Subject.objects.create(name='Science', code='SCI101', level='Grade 2')
        url = reverse('subject-assign-teacher', args=[subject.id])
        response = self.client.post(url, {'teacher_id': self.teacher.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['teacher_name'], self.teacher.full_name or self.teacher.email)

    def test_remove_teacher(self):
        subject = Subject.objects.create(name='Biology', code='BIO101', level='Grade 3', teacher_in_charge=self.teacher)
        url = reverse('subject-remove-teacher', args=[subject.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(Subject.objects.get(id=subject.id).teacher_in_charge)

    def test_statistics(self):
        Subject.objects.create(name='Art', code='ART101', level='Grade 4')
        Subject.objects.create(name='History', code='HIS101', level='Grade 4', teacher_in_charge=self.teacher)
        url = reverse('subject-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_subjects'], 2)
        self.assertEqual(response.data['assigned_subjects'], 1)

    def test_bulk_create(self):
        url = reverse('subject-bulk-create')
        subjects_payload = {
            'subjects': [
                {'name': 'Music', 'code': 'MUS101', 'level': 'Grade 1'},
                {'name': 'Drama', 'code': 'DRA101', 'level': 'Grade 1'}
            ]
        }
        response = self.client.post(url, subjects_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Subject.objects.count(), 2)
        print(response.status_code)
        print(response.data)

    def test_permissions_teacher_cannot_create(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('subject-list')
        response = self.client.post(url, self.subject_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
