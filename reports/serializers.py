# reports/serializers.py
from rest_framework import serializers
from exams.models import StudentScore, Term, Exam
from classes.models import Class


class ReportCardScoreSerializer(serializers.ModelSerializer):
    """Serializer for individual exam scores in a report card"""
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    max_score = serializers.IntegerField(source='exam.max_score', read_only=True)
    grade = serializers.CharField(read_only=True)
    
    class Meta:
        model = StudentScore
        fields = ['exam_name', 'score', 'max_score', 'grade']


class ReportCardSubjectPerformanceSerializer(serializers.Serializer):
    """Serializer for subject-wise performance aggregation"""
    subject_name = serializers.CharField()
    subject_code = serializers.CharField()
    scores = ReportCardScoreSerializer(many=True)
    subject_average = serializers.FloatField()


class ReportCardSerializer(serializers.Serializer):
    """Main serializer for complete report card data"""
    student_info = serializers.DictField()
    term_info = serializers.DictField()
    performance_by_subject = ReportCardSubjectPerformanceSerializer(many=True)
    summary = serializers.DictField()


class ReportPublishingSerializer(serializers.Serializer):
    """Serializer to validate input data for report publishing"""
    
    term_id = serializers.IntegerField(
        help_text="ID of the academic term for which to generate reports"
    )
    
    class_id = serializers.IntegerField(
        help_text="ID of the class for which to generate reports"
    )
    
    exam_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional: ID of specific exam. If not provided, generates term summary reports"
    )
    
    def validate_term_id(self, value):
        """Validate that the term exists"""
        try:
            Term.objects.get(id=value)
        except Term.DoesNotExist:
            raise serializers.ValidationError("Term with this ID does not exist")
        return value
    
    def validate_class_id(self, value):
        """Validate that the class exists"""
        try:
            Class.objects.get(id=value)
        except Class.DoesNotExist:
            raise serializers.ValidationError("Class with this ID does not exist")
        return value
    
    def validate_exam_id(self, value):
        """Validate that the exam exists if provided"""
        if value is not None:
            try:
                Exam.objects.get(id=value)
            except Exam.DoesNotExist:
                raise serializers.ValidationError("Exam with this ID does not exist")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        term_id = data.get('term_id')
        class_id = data.get('class_id')
        exam_id = data.get('exam_id')
        
        if exam_id:
            try:
                term = Term.objects.get(id=term_id)
                exam = Exam.objects.get(id=exam_id)
                
                if exam.term_id != term.id:
                    raise serializers.ValidationError(
                        "The specified exam does not belong to the specified term"
                    )
                
                if exam.classroom_id != class_id:
                    raise serializers.ValidationError(
                        "The specified exam does not belong to the specified class"
                    )
                    
            except Term.DoesNotExist:
                raise serializers.ValidationError("Invalid term ID")
            except Exam.DoesNotExist:
                raise serializers.ValidationError("Invalid exam ID")
        
        return data