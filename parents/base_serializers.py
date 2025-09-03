from rest_framework import serializers
from .models import ParentProfile

class ParentBasicInfoSerializer(serializers.ModelSerializer):
    """
    A minimal, dependency-free serializer for basic parent info.
    Used in other apps (like students) to avoid circular imports.
    """
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = ParentProfile
        fields = ['id', 'full_name', 'email', 'phone_number']