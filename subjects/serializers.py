from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Subject
from classes.models import Class
from schedules.models import ScheduleEntry

User = get_user_model()

class SubjectCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new subjects.
    
    Includes validation for teacher assignment and code uniqueness.
    """
    
    class Meta:
        model = Subject
        fields = [
            'name',
            'code',
            'description',
            'level',
            'teacher_in_charge'
        ]
        extra_kwargs = {
            'code': {
                'error_messages': {
                    'unique': 'A subject with this code already exists.'
                }
            }
        }
    
    def validate_code(self, value):
        """
        Validate and format the subject code.
        """
        if value:
            value = value.upper().strip()
            
            if not value.replace('-', '').replace('_', '').isalnum():
                raise serializers.ValidationError(
                    "Subject code must contain only letters, numbers, hyphens, and underscores."
                )
        
        return value
    
    def validate_teacher_in_charge(self, value):
        """
        Validate that the assigned teacher has the correct role and is active.
        """
        if value:
            if not hasattr(value, 'role') or value.role != 'TEACHER':
                raise serializers.ValidationError(
                    "Only users with TEACHER role can be assigned as teacher in charge."
                )
            
            if not value.is_active:
                raise serializers.ValidationError(
                    "Only active teachers can be assigned as teacher in charge."
                )
        
        return value
    
    def validate(self, attrs):
        """
        Validate the combination of fields.
        """
        # Check for duplicate subject name and level combination
        name = attrs.get('name')
        level = attrs.get('level')
        
        if name and level:
            existing = Subject.objects.filter(name__iexact=name, level=level)
            if existing.exists():
                raise serializers.ValidationError({
                    'name': f'A subject with the name "{name}" already exists for level "{level}".'
                })
        
        return attrs


class SubjectUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing subjects.
    
    Similar to create serializer but handles partial updates.
    """
    
    class Meta:
        model = Subject
        fields = [
            'name',
            'code',
            'description',
            'level',
            'teacher_in_charge'
        ]
        extra_kwargs = {
            'code': {
                'error_messages': {
                    'unique': 'A subject with this code already exists.'
                }
            }
        }
    
    def validate_code(self, value):
        """
        Validate and format the subject code.
        """
        if value:
            value = value.upper().strip()
            
            if not value.replace('-', '').replace('_', '').isalnum():
                raise serializers.ValidationError(
                    "Subject code must contain only letters, numbers, hyphens, and underscores."
                )
        
        return value
    
    def validate_teacher_in_charge(self, value):
        """
        Validate that the assigned teacher has the correct role and is active.
        """
        if value:
            if not hasattr(value, 'role') or value.role != 'TEACHER':
                raise serializers.ValidationError(
                    "Only users with TEACHER role can be assigned as teacher in charge."
                )
            
            if not value.is_active:
                raise serializers.ValidationError(
                    "Only active teachers can be assigned as teacher in charge."
                )
        
        return value
    
    def validate(self, attrs):
        """
        Validate the combination of fields for updates.
        """
        name = attrs.get('name')
        level = attrs.get('level')
        
        if name and level:
            existing = Subject.objects.filter(name__iexact=name, level=level)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise serializers.ValidationError({
                    'name': f'A subject with the name "{name}" already exists for level "{level}".'
                })
        
        return attrs


class SubjectListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing subjects with minimal information.
    
    Optimized for list views with essential fields only.
    """
    
    teacher_name = serializers.ReadOnlyField()
    teacher_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = [
            'id',
            'name',
            'code',
            'level',
            'teacher_name',
            'teacher_id',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_teacher_id(self, obj):
        """
        Get the ID of the teacher in charge.
        """
        return obj.teacher_in_charge.id if obj.teacher_in_charge else None

class SimpleClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['id', 'name']

class SubjectDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed subject information.
    
    Includes all fields and additional computed fields.
    """
    
    teacher_name = serializers.ReadOnlyField()
    teacher_details = serializers.SerializerMethodField()
    used_in_classes = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = [
            'id',
            'name',
            'code',
            'description',
            'level',
            'teacher_in_charge',
            'teacher_name',
            'teacher_details',
            'created_at',
            'updated_at',
            'used_in_classes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_teacher_details(self, obj):
        teacher = obj.teacher_in_charge
        if not teacher:
            return None
        return {
            'id': teacher.id,
            'name': teacher.full_name or teacher.email,
            'email': teacher.email,
        }
    
    def get_used_in_classes(self, obj):
        """
        Get a list of unique classes where this subject is scheduled.
        `obj` is the Subject instance.
        """
        class_ids = ScheduleEntry.objects.filter(subject=obj).values_list('classroom_id', flat=True).distinct()
        classes = Class.objects.filter(pk__in=class_ids)
        return SimpleClassSerializer(classes, many=True).data

class TeacherSubjectSerializer(serializers.ModelSerializer):
    """
    Serializer for subjects when viewed from a teacher's perspective.
    
    Minimal information for teacher-related views.
    """
    
    class Meta:
        model = Subject
        fields = [
            'id',
            'name',
            'code',
            'level',
            'description'
        ]
        read_only_fields = ['id']


class SubjectAssignmentSerializer(serializers.Serializer):
    """
    Serializer for teacher assignment operations.
    
    Used for custom actions like assign_teacher and remove_teacher.
    """
    
    teacher_id = serializers.IntegerField(required=True)
    
    def validate_teacher_id(self, value):
        """
        Validate that the teacher exists and has the correct role.
        """
        try:
            teacher = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Teacher not found.")
        
        if not hasattr(teacher, 'role') or teacher.role != 'TEACHER':
            raise serializers.ValidationError(
                "User must have TEACHER role to be assigned as teacher in charge."
            )
        
        if not teacher.is_active:
            raise serializers.ValidationError(
                "Only active teachers can be assigned as teacher in charge."
            )
        
        return value


class SubjectStatisticsSerializer(serializers.Serializer):
    """
    Serializer for subject statistics.
    
    Used for custom statistics endpoints.
    """
    
    total_subjects = serializers.IntegerField(read_only=True)
    assigned_subjects = serializers.IntegerField(read_only=True)
    unassigned_subjects = serializers.IntegerField(read_only=True)
    assignment_percentage = serializers.FloatField(read_only=True)
    level_distribution = serializers.DictField(read_only=True)
    subjects_by_teacher = serializers.DictField(read_only=True)


class SubjectBulkCreateSerializer(serializers.Serializer):
    """
    Serializer for bulk creating subjects.
    
    Accepts a list of subject data for batch operations.
    """
    
    subjects = SubjectCreateSerializer(many=True)
    
    def create(self, validated_data):
        """
        Create multiple subjects at once.
        """
        subjects_data = validated_data['subjects']
        subjects = []
        
        for subject_data in subjects_data:
            subject = Subject.objects.create(**subject_data)
            subjects.append(subject)
        
        return subjects
    
    def validate_subjects(self, value):
        """
        Validate that all subjects in the list are valid.
        """
        if not value:
            raise serializers.ValidationError("At least one subject is required.")
        
        if len(value) > 50:  # Limit bulk operations
            raise serializers.ValidationError("Cannot create more than 50 subjects at once.")
        
        # Check for duplicate codes within the batch
        codes = [subject.get('code') for subject in value if subject.get('code')]
        if len(codes) != len(set(codes)):
            raise serializers.ValidationError("Duplicate subject codes found in the batch.")
        
        return value