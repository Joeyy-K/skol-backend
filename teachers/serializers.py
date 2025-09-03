from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TeacherProfile
from rest_framework.authtoken.models import Token
from auth_system.serializers import UserSerializer, UserUpdateSerializer
from django.db.models.signals import post_save
from .signals import create_teacher_profile

User = get_user_model()

class TeacherProfileSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    user = serializers.DictField(write_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user_info', 'user', 'employee_id', 
            'specialization', 'date_of_hire', 'phone_number', 'bio',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        post_save.disconnect(create_teacher_profile, sender=User)
        
        try:
            user_data = validated_data.pop('user')
            
            user_create_serializer = UserSerializer(data=user_data)
            user_create_serializer.is_valid(raise_exception=True)
            user_instance = user_create_serializer.save(role='TEACHER')
            
            Token.objects.get_or_create(user=user_instance)
            teacher_profile = TeacherProfile.objects.create(user=user_instance, **validated_data)
        
        finally:
            post_save.connect(create_teacher_profile, sender=User)
            
        return teacher_profile

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