# auth_system/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from attendance.models import AttendanceRecord
from attendance.serializers import AttendanceRecordSerializer
from .models import User
from rest_framework.validators import UniqueValidator
from classes.models import Class
from subjects.models import Subject
from exams.models import Exam, StudentScore
from students.models import StudentProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'role', 'password', 'password_confirm']

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        """Validate password confirmation and strength"""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs

    def create(self, validated_data):
        """Create user with hashed password"""
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        remember_me = attrs.get('remember_me', False)

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            attrs['remember_me'] = remember_me
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role", 
            "is_active", "is_staff", "date_joined", "password"
        ]
        read_only_fields = ["id", "date_joined", "is_staff", "role"] # Role should be read-only here

        extra_kwargs = {
            'password': {'write_only': True, 'required': True} 
        }

    def create(self, validated_data):
        """
        Custom create method to ensure the password is hashed correctly.
        """
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user
    
class UserUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=False,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ["email", "full_name", "role", "is_active"]

class DashboardClassSerializer(serializers.ModelSerializer):
    """A lean serializer for classes on the teacher dashboard."""
    class Meta:
        model = Class
        fields = ['id', 'name', 'level']

class DashboardSubjectSerializer(serializers.ModelSerializer):
    """A lean serializer for subjects on the teacher dashboard."""
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'level']

class DashboardExamSerializer(serializers.ModelSerializer):
    """A lean serializer for exams on the teacher dashboard."""
    subject_name = serializers.CharField(source='subject.name')
    classroom_name = serializers.CharField(source='classroom.name')

    class Meta:
        model = Exam
        fields = ['id', 'name', 'date', 'subject_name', 'classroom_name']

class DashboardScoreSerializer(serializers.ModelSerializer):
    """A lean serializer for displaying a student's scores on their dashboard."""
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    exam_id = serializers.IntegerField(source='exam.id', read_only=True)
    subject_name = serializers.CharField(source='exam.subject.name', read_only=True)
    exam_max_score = serializers.IntegerField(source='exam.max_score', read_only=True)
    percentage = serializers.ReadOnlyField()
    grade = serializers.ReadOnlyField()

    class Meta:
        model = StudentScore
        fields = [
            'exam_id',
            'exam_name',
            'subject_name',
            'score',
            'exam_max_score',
            'percentage',
            'grade',
            'remarks'
        ]

class ParentDashboardChildSerializer(serializers.ModelSerializer):
    """
    A lean serializer for displaying a parent's child's information on the dashboard.
    Uses SerializerMethodField for dynamic data fetching.
    """
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True, default='N/A')
    
    # We will populate these two fields manually in the view for now to keep it simple
    recent_scores = serializers.SerializerMethodField()
    attendance_records = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = ['id', 'full_name', 'admission_number', 'classroom_name', 'recent_scores', 'attendance_records']
        
    def get_recent_scores(self, obj):
        """
        `obj` is the StudentProfile instance
        Get the 5 most recent scores for this student
        """
        scores = StudentScore.objects.filter(student=obj).select_related(
            'exam', 'exam__subject'
        ).order_by('-exam__date')[:5]
        return DashboardScoreSerializer(scores, many=True).data
        
    def get_attendance_records(self, obj):
        """
        Get the last 30 attendance records for this student
        """
        records = AttendanceRecord.objects.filter(student=obj).select_related(
            'classroom'
        ).order_by('-date')[:30]
        return AttendanceRecordSerializer(records, many=True).data

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate old password and new password confirmation"""
        user = self.context['request'].user
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        if not user.check_password(old_password):
            raise serializers.ValidationError({
                'old_password': 'Old password is incorrect.'
            })

        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match.'
            })

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': e.messages
            })

        return attrs

    def save(self):
        """Set the new password on the user"""
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user


class UpdateProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(
            queryset=User.objects.all(),
            message="A user with this email already exists."
        )]
    )

    class Meta:
        model = User
        fields = ['full_name', 'email']

    def validate_email(self, value):
        """Ensure email uniqueness while allowing current user's email"""
        user = self.instance
        if user and user.email == value:
            return value
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value