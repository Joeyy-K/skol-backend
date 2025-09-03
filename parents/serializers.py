from rest_framework import serializers
from .models import ParentProfile
from students.serializers import StudentProfileSerializer 
from auth_system.serializers import UserSerializer, UserUpdateSerializer


class ParentProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the ParentProfile model, handles create, update, and read.
    """
    user_info = UserSerializer(source='user', read_only=True)
    children_info = StudentProfileSerializer(source='children', many=True, read_only=True)

    user = serializers.DictField(write_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            'id', 'user_info', 'user', 'phone_number', 'address', 'children_info'
        ]
        read_only_fields = ['id', 'children_info']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        
        user_create_serializer = UserSerializer(data=user_data)
        user_create_serializer.is_valid(raise_exception=True)
        user = user_create_serializer.save(role='PARENT')
        
        parent_profile = ParentProfile.objects.create(user=user, **validated_data)
        return parent_profile

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        if user_data:
            user_instance = instance.user
            user_update_serializer = UserUpdateSerializer(
                user_instance, data=user_data, partial=True
            )
            user_update_serializer.is_valid(raise_exception=True)
            user_update_serializer.save()
        
        return super().update(instance, validated_data)

class LinkStudentSerializer(serializers.Serializer):
    """
    A simple serializer to validate the student_id for linking/unlinking.
    """
    student_id = serializers.IntegerField(required=True)

    def validate_student_id(self, value):
        from students.models import StudentProfile
        if not StudentProfile.objects.filter(pk=value).exists():
            raise serializers.ValidationError("A student with this ID does not exist.")
        return value