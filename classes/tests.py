# teachers/tests.py

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from classes.models import Class

User = get_user_model()

class ClassIntegrationTests(APITestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="adminpass",
            role="ADMIN",
            full_name="Admin One",
            is_staff=True
        )
        self.teacher = User.objects.create_user(
            email="teacher@example.com",
            password="teacherpass",
            role="TEACHER",
            full_name="Teacher One"
        )

        # Generate and attach token for the admin user
        self.token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_create_class_and_assign_teacher(self):
        # Create class
        create_response = self.client.post("/api/classes/", {
            "name": "Grade 8 North",
            "level": "Grade 8",
            "teacher_in_charge": None
        }, format="json")

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        class_id = create_response.data["data"]["id"]

        # Assign teacher
        assign_url = f"/api/classes/{class_id}/assign_teacher/"
        assign_response = self.client.post(assign_url, {
            "teacher_id": self.teacher.id
        }, format="json")

        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)
        self.assertEqual(assign_response.data["data"]["teacher_in_charge"], self.teacher.id)

    def test_list_classes(self):
        Class.objects.create(name="Grade 4 A", level="Grade 4")
        Class.objects.create(name="Grade 5 B", level="Grade 5")

        response = self.client.get("/api/classes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
