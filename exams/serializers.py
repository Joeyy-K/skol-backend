# exams/serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import Exam, StudentScore, Term

class TermSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Term
        fields = [
            'id', 'name', 'name_display', 'academic_year', 
            'start_date', 'end_date', 'is_active', 'display_name'
        ]
    
    def validate(self, data):
        """Validate that start_date is before end_date"""
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError("Start date must be before end date.")
        return data
    
    def validate_academic_year(self, value):
        """Validate academic year is reasonable"""
        if value < 2000 or value > 2100:
            raise serializers.ValidationError("Academic year must be between 2000 and 2100.")
        return value

class StudentScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_admission_number = serializers.CharField(source='student.admission_number', read_only=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    grade = serializers.CharField(read_only=True)
    
    class Meta:
        model = StudentScore
        fields = [
            'id', 'exam', 'student', 'student_name', 'student_admission_number',
            'score', 'percentage', 'grade', 'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_score(self, value):
        """Validate score doesn't exceed the exam's max score."""
        exam = None
        if self.instance:
            exam = self.instance.exam
        elif 'exam' in self.initial_data:
            try:
                exam = Exam.objects.get(pk=self.initial_data['exam'])
            except Exam.DoesNotExist:
                raise serializers.ValidationError("Exam not found.")

        if not exam:
            raise serializers.ValidationError("Exam context is required to validate the score.")
        
        if float(value) > exam.max_score:
            raise serializers.ValidationError(
                f"Score ({value}) cannot exceed the exam's maximum score of {exam.max_score}."
            )
        
        return value

class ExamSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    term_name = serializers.CharField(source='term.display_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    scores = StudentScoreSerializer(many=True, read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    highest_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    lowest_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    student_scores = StudentScoreSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'subject', 'subject_name', 'classroom', 'classroom_name',
            'date', 'term', 'term_name', 'created_by', 'created_by_name', 'max_score',
            'scores', 'student_scores', 'total_students', 'average_score', 
            'highest_score', 'lowest_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create exam with optional student scores"""
        student_scores_data = validated_data.pop('student_scores', [])
        
        with transaction.atomic():
            exam = Exam.objects.create(**validated_data)
            
            for score_data in student_scores_data:
                score_data['exam'] = exam
                StudentScore.objects.create(**score_data)
            
            return exam
    
    def update(self, instance, validated_data):
        """Update exam and optionally update scores"""
        student_scores_data = validated_data.pop('student_scores', [])
        
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            if student_scores_data:
                instance.scores.all().delete()
                for score_data in student_scores_data:
                    score_data['exam'] = instance
                    StudentScore.objects.create(**score_data)
            
            return instance


class ExamStatisticsSerializer(serializers.Serializer):
    """Serializer for exam statistics"""
    total_students = serializers.IntegerField()
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    highest_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    lowest_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    pass_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    grade_distribution = serializers.DictField()