from rest_framework import serializers
from .models import AttendanceRecord

class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField(read_only=True)
    student_admission_number = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'student', 'classroom', 'date', 'status', 'taken_by',
            'created_at', 'updated_at', 'student_name', 'student_admission_number'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_student_name(self, obj):
        return obj.student.user.full_name
    
    def get_student_admission_number(self, obj):
        return obj.student.admission_number

class DailyAttendanceSheetSerializer(serializers.Serializer):
    records = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        allow_empty=True
    )
    
    def validate_records(self, value):
        """
        Validate that each record has required fields with correct types
        """
        validated_records = []
        
        for record in value:
            if 'student_id' not in record:
                raise serializers.ValidationError("Each record must have 'student_id'")
            if 'status' not in record:
                raise serializers.ValidationError("Each record must have 'status'")
            
            try:
                student_id = int(record['student_id'])
            except (ValueError, TypeError):
                raise serializers.ValidationError("student_id must be a valid integer")
            
            status = record['status']
            valid_statuses = ['PRESENT', 'ABSENT', 'LATE']
            if status not in valid_statuses:
                raise serializers.ValidationError(f"status must be one of: {valid_statuses}")
            
            validated_records.append({
                'student_id': student_id,
                'status': status
            })
        
        return validated_records