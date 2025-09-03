from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from datetime import date, timedelta, datetime
from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from rest_framework.views import APIView
from auth_system.permissions import IsParentUser
from exams.models import Term

from .models import AttendanceRecord
from .permissions import IsTeacherInChargeOrAdmin, CanViewAttendance
from .serializers import (
    AttendanceRecordSerializer, 
    DailyAttendanceSheetSerializer,
)
from students.models import StudentProfile
from classes.models import Class

class IsAdminOrTeacher(IsAuthenticated):
    """
    Custom permission to only allow admins and teachers to access attendance.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        user_role = getattr(request.user, 'role', None)
        return user_role in ['ADMIN', 'TEACHER']

class AttendanceViewSet(viewsets.ViewSet):
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['sheet'] and self.request.method == 'GET':
            permission_classes = [CanViewAttendance]
        elif self.action in ['sheet'] and self.request.method == 'POST':
            permission_classes = [IsTeacherInChargeOrAdmin]
        elif self.action in ['summary', 'history', 'analytics']:
            permission_classes = [CanViewAttendance]
        else:
            permission_classes = [IsAdminOrTeacher]
        
        return [permission() for permission in permission_classes]
    
    def sheet(self, request):
        """
        Handle attendance sheet operations:
        - GET: Retrieve attendance sheet for a class on a specific date (any teacher)
        - POST: Save/update attendance records for a class on a specific date (only assigned teacher)
        """
        if request.method == 'GET':
            return self._handle_get_sheet(request)
        elif request.method == 'POST':
            return self._handle_post_sheet(request)
    
    def _handle_get_sheet(self, request):
        """
        GET /api/attendance/sheet/?class_id=1&date=2024-01-15
        
        Returns all students in the class with their attendance status for the date.
        Now includes metadata about who can edit and when it was last updated.
        """
        class_id = request.query_params.get('class_id')
        date_str = request.query_params.get('date')
        
        if not class_id:
            return Response(
                {'error': 'class_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not date_str:
            return Response(
                {'error': 'date parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        classroom = get_object_or_404(Class, id=class_id)
        
        can_edit = (
            request.user.role == 'ADMIN' or
            (request.user.role == 'TEACHER' and classroom.teacher_in_charge == request.user)
        )
        
        students = StudentProfile.objects.filter(classroom=classroom).select_related('user')
        
        attendance_records = AttendanceRecord.objects.filter(
            classroom=classroom,
            date=date_obj
        ).select_related('student__user', 'taken_by')
        
        attendance_map = {}
        last_updated_info = {}
        
        for record in attendance_records:
            attendance_map[record.student.id] = record.status
            last_updated_info[record.student.id] = {
                'updated_at': record.updated_at,
                'taken_by': record.taken_by.full_name if record.taken_by else 'System',
                'taken_by_id': record.taken_by.id if record.taken_by else None
            }
        
        sheet_data = []
        for student in students:
            student_data = {
                'student_id': student.id,
                'student_name': student.user.full_name,
                'admission_number': student.admission_number,
                'status': attendance_map.get(student.id, None)
            }
            
            if student.id in last_updated_info:
                student_data['last_updated'] = last_updated_info[student.id]
            
            sheet_data.append(student_data)
        
        return Response({
            'class_id': class_id,
            'class_name': classroom.name,
            'date': date_str,
            'can_edit': can_edit,
            'teacher_in_charge': classroom.teacher_in_charge.full_name if classroom.teacher_in_charge else None,
            'students': sheet_data
        })
    
    def _handle_post_sheet(self, request):
        """
        POST /api/attendance/sheet/
        Body: {
            "class_id": 1,
            "date": "2024-01-15",
            "records": [
                {"student_id": 1, "status": "PRESENT"},
                {"student_id": 2, "status": "ABSENT"},
                {"student_id": 3, "status": "LATE"}
            ]
        }
        """
        class_id = request.data.get('class_id')
        date_str = request.data.get('date')
        
        if not class_id:
            return Response(
                {'error': 'class_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not date_str:
            return Response(
                {'error': 'date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # --- TERM VALIDATION LOGIC ---
        try:
            active_term = Term.objects.get(is_active=True)
            if not (active_term.start_date <= date_obj <= active_term.end_date):
                return Response(
                    {'error': f"The selected date ({date_str}) is outside the active term dates ({active_term.start_date} to {active_term.end_date})."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Term.DoesNotExist:
            return Response(
                {'error': 'There is no active term set. Attendance cannot be recorded.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Term.MultipleObjectsReturned:
            return Response(
                {'error': 'Multiple active terms found. Please contact an administrator.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if date_obj > date.today():
            return Response(
                {'error': 'Cannot mark attendance for future dates'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        classroom = get_object_or_404(Class, id=class_id)
        
        serializer = DailyAttendanceSheetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        records = serializer.validated_data['records']
        
        try:
            with transaction.atomic():
                updated_count = 0
                created_count = 0
                changes_log = []
                
                for record in records:
                    student_id = record['student_id']
                    attendance_status = record['status']
                    
                    try:
                        student = StudentProfile.objects.get(
                            id=student_id,
                            classroom=classroom
                        )
                    except StudentProfile.DoesNotExist:
                        return Response(
                            {'error': f'Student with id {student_id} not found in class {classroom.name}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    existing_record = AttendanceRecord.objects.filter(
                        student=student,
                        classroom=classroom,
                        date=date_obj
                    ).first()
                    
                    old_status = existing_record.status if existing_record else None
                    
                    attendance_record, created = AttendanceRecord.objects.update_or_create(
                        student=student,
                        classroom=classroom,
                        date=date_obj,
                        defaults={
                            'status': attendance_status,
                            'taken_by': request.user
                        }
                    )
                    
                    if created:
                        created_count += 1
                        changes_log.append({
                            'student': student.user.full_name,
                            'change': f'Created: {attendance_status}'
                        })
                    else:
                        updated_count += 1
                        if old_status != attendance_status:
                            changes_log.append({
                                'student': student.user.full_name,
                                'change': f'Changed: {old_status} → {attendance_status}'
                            })
                
                return Response({
                    'message': 'Attendance records saved successfully',
                    'created': created_count,
                    'updated': updated_count,
                    'total': len(records),
                    'changes': changes_log,
                    'saved_by': request.user.full_name,
                    'saved_at': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to save attendance records: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """
        GET /api/attendance/history/?class_id=1&student_id=2&start_date=2024-01-01&end_date=2024-01-31
        
        Returns attendance history with filters for class, student, and date range.
        Supports pagination for large datasets.
        """
        class_id = request.query_params.get('class_id')
        student_id = request.query_params.get('student_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        # Default to last 30 days if no date range provided
        if not start_date_str:
            start_date = date.today() - timedelta(days=30)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        if not end_date_str:
            end_date = date.today()
        else:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        queryset = AttendanceRecord.objects.select_related(
            'student__user', 'classroom', 'taken_by'
        ).filter(date__range=[start_date, end_date])
        
        if class_id:
            queryset = queryset.filter(classroom_id=class_id)
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        queryset = queryset.order_by('-date', 'student__user__first_name')
        
        history_by_date = {}
        for record in queryset:
            date_key = record.date.strftime('%Y-%m-%d')
            if date_key not in history_by_date:
                history_by_date[date_key] = []
            
            history_by_date[date_key].append({
                'student_id': record.student.id,
                'student_name': record.student.user.full_name,
                'admission_number': record.student.admission_number,
                'class_name': record.classroom.name,
                'status': record.status,
                'taken_by': record.taken_by.full_name if record.taken_by else 'System',
                'updated_at': record.updated_at,
                'created_at': record.created_at
            })
        
        return Response({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_records': queryset.count(),
            'history': history_by_date
        })
    
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        GET /api/attendance/summary/?class_id=1&year=2025&month=7
        
        Returns a summary of attendance for each day in a given month for a class.
        Enhanced with additional analytics.
        """
        class_id = request.query_params.get('class_id')
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')

        if not all([class_id, year_str, month_str]):
            return Response(
                {'error': 'class_id, year, and month parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            year, month = int(year_str), int(month_str)
            start_date = date(year, month, 1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year or month'}, status=status.HTTP_400_BAD_REQUEST)
        
        classroom = get_object_or_404(Class, id=class_id)
        total_students = StudentProfile.objects.filter(classroom=classroom).count()
        
        summary_data = AttendanceRecord.objects.filter(
            classroom_id=class_id,
            date__range=[start_date, end_date]
        ).values('date').annotate(
            present_count=Count('pk', filter=Q(status='PRESENT')),
            absent_count=Count('pk', filter=Q(status='ABSENT')),
            late_count=Count('pk', filter=Q(status='LATE')),
            total_marked=Count('pk')
        ).order_by('date')
        
        daily_summary = {}
        total_days_with_attendance = 0
        
        for item in summary_data:
            if item['date']:
                date_str = item['date'].strftime('%Y-%m-%d')
                daily_summary[date_str] = {
                    'present': item['present_count'],
                    'absent': item['absent_count'],
                    'late': item['late_count'],
                    'total_marked': item['total_marked'],
                    'attendance_rate': round((item['present_count'] / item['total_marked'] * 100), 2) if item['total_marked'] > 0 else 0,
                    'unmarked_count': max(0, total_students - item['total_marked'])
                }
                total_days_with_attendance += 1
        
        return Response({
            'class_name': classroom.name,
            'total_students': total_students,
            'period': f"{year}-{month:02d}",
            'total_days_with_attendance': total_days_with_attendance,
            'daily_summary': daily_summary
        })
    
    @action(detail=False, methods=['get'], url_path='analytics')
    def analytics(self, request):
        """
        GET /api/attendance/analytics/?class_id=1&start_date=2024-01-01&end_date=2024-01-31
        
        Returns detailed analytics for attendance patterns.
        """
        class_id = request.query_params.get('class_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if not class_id:
            return Response({'error': 'class_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not start_date_str or not end_date_str:
            today = date.today()
            start_date = today.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        classroom = get_object_or_404(Class, id=class_id)
        
        students_analytics = AttendanceRecord.objects.filter(
            classroom=classroom,
            date__range=[start_date, end_date]
        ).values(
            'student__id',
            'student__user__full_name',
            'student__admission_number'
        ).annotate(
            total_days=Count('id'),
            present_days=Count('id', filter=Q(status='PRESENT')),
            absent_days=Count('id', filter=Q(status='ABSENT')),
            late_days=Count('id', filter=Q(status='LATE'))
        ).order_by('student__user__full_name')
        
        student_stats = []
        for student in students_analytics:
            attendance_rate = (student['present_days'] / student['total_days'] * 100) if student['total_days'] > 0 else 0
            student_stats.append({
                'student_id': student['student__id'],
                'student_name': f"{student['student__user__full_name']}",
                'admission_number': student['student__admission_number'],
                'total_days': student['total_days'],
                'present_days': student['present_days'],
                'absent_days': student['absent_days'],
                'late_days': student['late_days'],
                'attendance_rate': round(attendance_rate, 2)
            })
        
        total_records = AttendanceRecord.objects.filter(
            classroom=classroom,
            date__range=[start_date, end_date]
        ).count()
        
        overall_stats = AttendanceRecord.objects.filter(
            classroom=classroom,
            date__range=[start_date, end_date]
        ).aggregate(
            total_present=Count('id', filter=Q(status='PRESENT')),
            total_absent=Count('id', filter=Q(status='ABSENT')),
            total_late=Count('id', filter=Q(status='LATE'))
        )
        
        overall_attendance_rate = (overall_stats['total_present'] / total_records * 100) if total_records > 0 else 0
        
        return Response({
            'class_name': classroom.name,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'overall_statistics': {
                'total_records': total_records,
                'total_present': overall_stats['total_present'],
                'total_absent': overall_stats['total_absent'],
                'total_late': overall_stats['total_late'],
                'overall_attendance_rate': round(overall_attendance_rate, 2)
            },
            'student_statistics': student_stats
        })
    
class PersonalAttendanceView(APIView):
    """
    Provides attendance data for the logged-in user's context.
    - For a PARENT, returns data for all their linked children.
    - For a STUDENT, returns data for themselves.
    """
    class CanViewPersonalAttendance(IsAuthenticated):
        def has_permission(self, request, view):
            return super().has_permission(request, view) and request.user.role in ['PARENT', 'STUDENT']
            
    permission_classes = [CanViewPersonalAttendance]

    def get(self, request):
        user = request.user
        
        student_profiles = []

        if user.role == 'PARENT':
            try:
                parent_profile = user.parent_profile
                student_profiles = parent_profile.children.all().select_related('user', 'classroom')
            except user.parent_profile.DoesNotExist:
                pass 
        
        elif user.role == 'STUDENT':
            try:
                student_profiles = [user.student_profile]
            except user.student_profile.DoesNotExist:
                pass

        response_data = []
        for profile in student_profiles:
            records = AttendanceRecord.objects.filter(student=profile).order_by('-date')
            serializer = AttendanceRecordSerializer(records, many=True)
            response_data.append({
                'child_id': profile.id, 
                'child_name': profile.user.full_name,
                'records': serializer.data,
            })
            
        return Response(response_data)