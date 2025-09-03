from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Class
from students.base_serializers import StudentBasicInfoSerializer

User = get_user_model()


class TeacherBasicSerializer(serializers.ModelSerializer):
    """
    Basic serializer for Teacher information in Class responses.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id','full_name', 'email']
        read_only_fields = ['id', 'full_name', 'email']

    def get_full_name(self, obj):
        return f"{obj.full_name}".strip()


class ClassListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing classes with basic information.
    """
    teacher_in_charge_info = TeacherBasicSerializer(source='teacher_in_charge', read_only=True)
    teacher_name = serializers.ReadOnlyField()
    is_teacher_assigned = serializers.ReadOnlyField()

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'level', 'teacher_in_charge', 'teacher_in_charge_info',
            'teacher_name', 'is_teacher_assigned', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClassDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual class operations.
    """
    teacher_in_charge_info = TeacherBasicSerializer(source='teacher_in_charge', read_only=True)
    teacher_name = serializers.ReadOnlyField()
    is_teacher_assigned = serializers.ReadOnlyField()
    students = StudentBasicInfoSerializer(many=True, read_only=True)

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'level', 'teacher_in_charge', 'teacher_in_charge_info',
            'teacher_name', 'is_teacher_assigned', 'created_at', 'updated_at', 'students'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_teacher_in_charge(self, value):
        """
        Validate that the teacher_in_charge has TEACHER role and is active.
        """
        if value:
            if not hasattr(value, 'role'):
                raise serializers.ValidationError("User must have a role field.")
            
            if value.role != 'TEACHER':
                raise serializers.ValidationError("Only users with TEACHER role can be assigned as teacher in charge.")
            
            if not value.is_active:
                raise serializers.ValidationError("Teacher must be an active user.")
        
        return value

    def validate_name(self, value):
        """
        Validate class name format and uniqueness.
        """
        if not value.strip():
            raise serializers.ValidationError("Class name cannot be empty.")
        
        if self.instance:
            existing_class = Class.objects.filter(name__iexact=value.strip()).exclude(pk=self.instance.pk).first()
            if existing_class:
                raise serializers.ValidationError(f"A class with the name '{value}' already exists.")
        
        return value.strip()

    def validate_level(self, value):
        """
        Validate class level format.
        """
        if not value.strip():
            raise serializers.ValidationError("Class level cannot be empty.")
        
        return value.strip()


class ClassCreateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for creating new classes.
    """
    class Meta:
        model = Class
        fields = ['name', 'level', 'teacher_in_charge']

    def validate_teacher_in_charge(self, value):
        """
        Validate that the teacher_in_charge has TEACHER role and is active.
        """
        if value:
            if not hasattr(value, 'role'):
                raise serializers.ValidationError("User must have a role field.")
            
            if value.role != 'TEACHER':
                raise serializers.ValidationError("Only users with TEACHER role can be assigned as teacher in charge.")
            
            if not value.is_active:
                raise serializers.ValidationError("Teacher must be an active user.")
        
        return value

    def validate_name(self, value):
        """
        Validate class name format and uniqueness.
        """
        if not value.strip():
            raise serializers.ValidationError("Class name cannot be empty.")
        
        # Check for uniqueness during creation
        if Class.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError(f"A class with the name '{value}' already exists.")
        
        return value.strip()

    def validate_level(self, value):
        """
        Validate class level format.
        """
        if not value.strip():
            raise serializers.ValidationError("Class level cannot be empty.")
        
        return value.strip()

    def create(self, validated_data):
        """
        Create a new class instance.
        """
        return Class.objects.create(**validated_data)


class ClassUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for updating existing classes.
    """
    class Meta:
        model = Class
        fields = ['name', 'level', 'teacher_in_charge']

    def validate_teacher_in_charge(self, value):
        """
        Validate that the teacher_in_charge has TEACHER role and is active.
        """
        if value:
            if not hasattr(value, 'role'):
                raise serializers.ValidationError("User must have a role field.")
            
            if value.role != 'TEACHER':
                raise serializers.ValidationError("Only users with TEACHER role can be assigned as teacher in charge.")
            
            if not value.is_active:
                raise serializers.ValidationError("Teacher must be an active user.")
        
        return value

    def validate_name(self, value):
        """
        Validate class name format and uniqueness during update.
        """
        if not value.strip():
            raise serializers.ValidationError("Class name cannot be empty.")
        
        # Check for uniqueness during update (exclude current instance)
        if self.instance:
            existing_class = Class.objects.filter(name__iexact=value.strip()).exclude(pk=self.instance.pk).first()
            if existing_class:
                raise serializers.ValidationError(f"A class with the name '{value}' already exists.")
        
        return value.strip()

    def validate_level(self, value):
        """
        Validate class level format.
        """
        if not value.strip():
            raise serializers.ValidationError("Class level cannot be empty.")
        
        return value.strip()

    def update(self, instance, validated_data):
        """
        Update an existing class instance.
        """
        instance.name = validated_data.get('name', instance.name)
        instance.level = validated_data.get('level', instance.level)
        instance.teacher_in_charge = validated_data.get('teacher_in_charge', instance.teacher_in_charge)
        instance.save()
        return instance
    
class ClassForSelectSerializer(serializers.ModelSerializer):
    """
    A minimal serializer for populating class selection dropdowns.
    """
    class Meta:
        model = Class
        fields = ['id', 'name']