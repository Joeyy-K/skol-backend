# students/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import StudentProfile
from rest_framework.authtoken.models import Token
from auth_system.serializers import UserSerializer, UserUpdateSerializer 
from django.db.models.signals import post_save
from .signals import create_student_profile
from classes.serializers import ClassListSerializer 
from parents.models import ParentProfile
from parents.base_serializers import ParentBasicInfoSerializer

User = get_user_model()

class StudentProfileSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    user = serializers.DictField(write_only=True)
    classroom_info = ClassListSerializer(source='classroom', read_only=True)
    parent_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    parents = ParentBasicInfoSerializer(many=True, read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'id',
            'user_info',
            'user',
            'classroom',
            'classroom_info',
            'parent_id',
            'parents',
            'admission_number',
            'date_of_birth',
            'address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {'classroom': {'write_only': True}}

    def _handle_parent_relationship(self, student_profile, parent_id):
        """
        Helper method to handle parent-student relationship consistently.
        """
        if parent_id is not None:
            current_parents = student_profile.parents.all()
            for parent in current_parents:
                parent.children.remove(student_profile)
            
            if parent_id:  
                try:
                    parent_profile = ParentProfile.objects.get(pk=parent_id)
                    parent_profile.children.add(student_profile)
                except ParentProfile.DoesNotExist:
                    pass

    def create(self, validated_data):
        """
        Handle creation of the StudentProfile and its nested User.
        """
        parent_id = validated_data.pop('parent_id', None)
        
        post_save.disconnect(create_student_profile, sender=User)
        
        try:
            user_data = validated_data.pop('user')
            user_create_serializer = UserSerializer(data=user_data)
            user_create_serializer.is_valid(raise_exception=True)
            user_instance = user_create_serializer.save(role='STUDENT')
            
            Token.objects.get_or_create(user=user_instance)
            
            student_profile = StudentProfile.objects.create(user=user_instance, **validated_data)
            
            self._handle_parent_relationship(student_profile, parent_id)
            
            return student_profile
            
        finally:
            post_save.connect(create_student_profile, sender=User)

    def update(self, instance, validated_data):
        """
        Handle updates for the StudentProfile and its nested User.
        """
        parent_id = validated_data.pop('parent_id', None)
        
        user_data = validated_data.pop('user', None)
        if user_data:
            user_instance = instance.user
            user_update_serializer = UserUpdateSerializer(
                user_instance, data=user_data, partial=True
            )
            user_update_serializer.is_valid(raise_exception=True)
            user_update_serializer.save()
        
        updated_instance = super().update(instance, validated_data)
        
        self._handle_parent_relationship(updated_instance, parent_id)
        
        return updated_instance

class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """Limited serializer for students updating their own profiles"""
    class Meta:
        model = StudentProfile
        fields = ['address']

class StudentUserSerializer(serializers.ModelSerializer):
    """Serializer for the User part of student data"""
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']