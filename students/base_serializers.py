from rest_framework import serializers
from .models import StudentProfile

class StudentBasicInfoSerializer(serializers.ModelSerializer):
    """
    A minimal, dependency-free serializer for basic student info.
    Used in other apps to avoid circular imports.
    """
    full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = ['id', 'full_name', 'admission_number']