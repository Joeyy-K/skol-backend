# reports/views.py
from collections import defaultdict
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from students.models import StudentProfile
from exams.models import Term, StudentScore, Exam
from .serializers import ReportCardSerializer, ReportCardScoreSerializer, ReportCardSubjectPerformanceSerializer
from auth_system.permissions import IsParentUser, IsAdminUser
from django.db import transaction

from classes.models import Class
from students.models import StudentProfile
from .models import Report
from .serializers import ReportPublishingSerializer, ReportCardSerializer
import logging

logger = logging.getLogger(__name__)

class IsAdminOrTeacher(IsAuthenticated):
    """
    Custom permission to only allow admins or teachers to access report cards.
    """
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and
            request.user.role in ['ADMIN', 'TEACHER']
        )


class ReportCardDataView(APIView):
    """
    API view to generate and retrieve student report card data.
    """
    permission_classes = [IsAdminOrTeacher]
    
    def get(self, request):
        student_id = request.query_params.get('student_id')
        term_id = request.query_params.get('term_id')
        
        if not student_id:
            return Response(
                {'error': 'student_id query parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not term_id:
            return Response(
                {'error': 'term_id query parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        student = get_object_or_404(StudentProfile, id=student_id)
        term = get_object_or_404(Term, id=term_id)
        
        student_scores = StudentScore.objects.filter(
            student=student,
            exam__term=term
        ).select_related('exam', 'exam__subject').order_by('exam__subject__name', 'exam__name')
        
        if not student_scores.exists():
            return Response(
                {'error': 'No scores found for this student in the specified term'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        scores_by_subject = defaultdict(list)
        for score in student_scores:
            subject_key = (score.exam.subject.name, score.exam.subject.code)
            scores_by_subject[subject_key].append(score)
        
        total_marks_obtained = 0
        total_max_marks = 0
        
        performance_data_for_serializer = []
        for (subject_name, subject_code), scores in scores_by_subject.items():
            subject_total = sum(float(score.score) for score in scores)
            subject_max_total = sum(score.exam.max_score for score in scores)
            subject_average = (subject_total / subject_max_total * 100) if subject_max_total > 0 else 0
            
            total_marks_obtained += subject_total
            total_max_marks += subject_max_total
            
            # Clean score data without nested objects
            clean_scores = []
            for score in scores:
                clean_scores.append({
                    'exam_name': score.exam.name,
                    'score': float(score.score),
                    'max_score': score.exam.max_score,
                    'grade': score.grade,
                    'percentage': float(score.percentage) if score.percentage else 0
                })
            
            performance_data_for_serializer.append({
                'subject_name': subject_name,
                'subject_code': subject_code,
                'scores': clean_scores,
                'subject_average': round(subject_average, 2),
                'total_score': subject_total,
                'max_possible_score': subject_max_total,
                'exam_count': len(scores)
            })
        
        overall_percentage = (total_marks_obtained / total_max_marks * 100) if total_max_marks > 0 else 0
        
        def calculate_final_grade(percentage):
            if percentage >= 90:
                return 'A+'
            elif percentage >= 80:
                return 'A'
            elif percentage >= 70:
                return 'B+'
            elif percentage >= 60:
                return 'B'
            elif percentage >= 50:
                return 'C+'
            elif percentage >= 40:
                return 'C'
            elif percentage >= 30:
                return 'D'
            else:
                return 'F'
        
        final_grade = calculate_final_grade(overall_percentage)
        
        report_card_data = {
            'student_info': {
                'full_name': student.user.full_name,  # Changed from 'name' to 'full_name'
                'admission_number': getattr(student, 'admission_number', f'STU-{student.id:04d}'),
                'class': student.classroom.name if student.classroom else 'Not Assigned',  # Changed from 'class_name' to 'class'
                'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None
            },
            'term_info': {
                'term_name': term.get_name_display(),  # Changed from 'name' to 'term_name'
                'academic_year': term.academic_year,
                'display_name': term.display_name,
                'start_date': term.start_date.isoformat(),  # Changed from strftime to isoformat
                'end_date': term.end_date.isoformat()       # Changed from strftime to isoformat
            },
            'performance_by_subject': performance_data_for_serializer,
            'summary': {
                'total_subjects': len(scores_by_subject),
                'total_marks_obtained': total_marks_obtained,
                'total_max_marks': total_max_marks,
                'overall_average': round(overall_percentage, 2),  # Changed from 'overall_percentage'
                'final_grade': final_grade,
                'exam_type': 'Term Summary',
                'generated_date': term.end_date.isoformat()
            }
        }
        
        serializer = ReportCardSerializer(report_card_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _generate_report_card_data(self, student, term, exam=None):
        """
        Generate report card JSON data for a student and term.
        This reuses the logic from ReportCardDataView but returns consistent structure.
        """
        try:
            if exam:
                scores_queryset = StudentScore.objects.filter(
                    student=student,
                    exam=exam
                ).select_related('exam__subject')
            else:
                scores_queryset = StudentScore.objects.filter(
                    student=student,
                    exam__term=term
                ).select_related('exam__subject')
            
            subjects_data = {}
            for score in scores_queryset:
                subject_name = score.exam.subject.name
                subject_code = score.exam.subject.code
                
                if subject_name not in subjects_data:
                    subjects_data[subject_name] = {
                        'subject_name': subject_name,
                        'subject_code': subject_code,
                        'scores': [],
                        'total_score': 0,
                        'max_possible_score': 0,
                        'exam_count': 0
                    }
                
                # Clean score data without nested objects
                subjects_data[subject_name]['scores'].append({
                    'exam_name': score.exam.name,
                    'score': float(score.score),
                    'max_score': score.exam.max_score,
                    'grade': score.grade,
                    'percentage': float(score.percentage) if score.percentage else 0
                })
                
                subjects_data[subject_name]['total_score'] += float(score.score)
                subjects_data[subject_name]['max_possible_score'] += score.exam.max_score
                subjects_data[subject_name]['exam_count'] += 1
            
            performance_by_subject = []
            overall_total = 0
            overall_max = 0
            
            for subject_data in subjects_data.values():
                if subject_data['max_possible_score'] > 0:
                    subject_average = (subject_data['total_score'] / subject_data['max_possible_score']) * 100
                else:
                    subject_average = 0
                
                subject_data['subject_average'] = round(subject_average, 2)
                performance_by_subject.append(subject_data)
                
                overall_total += subject_data['total_score']
                overall_max += subject_data['max_possible_score']
            
            overall_average = (overall_total / overall_max * 100) if overall_max > 0 else 0
            
            def calculate_final_grade(percentage):
                if percentage >= 90:
                    return 'A+'
                elif percentage >= 80:
                    return 'A'
                elif percentage >= 70:
                    return 'B+'
                elif percentage >= 60:
                    return 'B'
                elif percentage >= 50:
                    return 'C+'
                elif percentage >= 40:
                    return 'C'
                elif percentage >= 30:
                    return 'D'
                else:
                    return 'F'
            
            final_grade = calculate_final_grade(overall_average)
            
            report_card_data = {
                'student_info': {
                    'admission_number': student.admission_number,
                    'full_name': student.user.full_name,
                    'class': student.classroom.name if student.classroom else '',
                    'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
                },
                'term_info': {
                    'term_name': term.get_name_display(),
                    'academic_year': term.academic_year,
                    'display_name': term.display_name,
                    'start_date': term.start_date.isoformat(),
                    'end_date': term.end_date.isoformat(),
                },
                'performance_by_subject': performance_by_subject,
                'summary': {
                    'total_subjects': len(subjects_data),
                    'overall_average': round(overall_average, 2),
                    'total_score': overall_total,
                    'max_possible_score': overall_max,
                    'final_grade': final_grade,
                    'exam_type': exam.name if exam else 'Term Summary',
                    'generated_date': term.end_date.isoformat()
                }
            }
            
            return report_card_data
            
        except Exception as e:
            logger.error(f"Error generating report data for student {student.admission_number}: {str(e)}")
            raise

class ParentReportCardDataView(APIView):
    """
    API view for a parent to generate a report card for THEIR OWN child.
    """
    permission_classes = [IsParentUser]

    def get(self, request):
        student_id = request.query_params.get('student_id')
        term_id = request.query_params.get('term_id')

        if not student_id or not term_id:
            return Response(
                {'error': 'student_id and term_id query parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parent_profile = request.user.parent_profile
        if not parent_profile.children.filter(pk=student_id).exists():
            return Response(
                {'error': "You do not have permission to view this student's report."},
                status=status.HTTP_403_FORBIDDEN
            )

        report_view = ReportCardDataView()
        report_view.request = request 
        return report_view.get(request)
    

class ReportPublishingView(APIView):
    """
    Admin view to generate and publish report cards for an entire class.
    Creates Report instances for all students in a class for a specific term.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """Generate and publish report cards for all students in a class"""
        serializer = ReportPublishingSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        term_id = serializer.validated_data['term_id']
        class_id = serializer.validated_data['class_id']
        exam_id = serializer.validated_data.get('exam_id')
        
        try:
            term = get_object_or_404(Term, id=term_id)
            classroom = get_object_or_404(Class, id=class_id)
            exam = None
            
            if exam_id:
                exam = get_object_or_404(Exam, id=exam_id, term=term)
                if exam.classroom_id != class_id:
                    return Response(
                        {'error': 'Exam does not belong to the specified class'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            students = StudentProfile.objects.filter(
                classroom_id=class_id
            ).select_related('user').order_by('admission_number')
            
            if not students.exists():
                return Response(
                    {'error': 'No students found in the specified class'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            with transaction.atomic():
                reports_created = 0
                reports_updated = 0
                errors = []
                
                for student in students:
                    try:
                        report_view = ReportCardDataView()
                        report_data = report_view._generate_report_card_data(student, term, exam)
                        
                        if exam:
                            title = f"{term.get_name_display()} {term.academic_year} - {exam.name}"
                        else:
                            title = f"{term.get_name_display()} {term.academic_year} - Term Report"
                        
                        report, created = Report.objects.update_or_create(
                            student=student,
                            term=term,
                            exam=exam,
                            defaults={
                                'title': title,
                                'report_data': report_data,
                                'is_published': True,
                                'generated_by': request.user,
                            }
                        )
                        
                        if created:
                            reports_created += 1
                        else:
                            reports_updated += 1
                            
                    except Exception as e:
                        error_msg = f"Failed to generate report for student {student.admission_number}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                return Response({
                    'success': True,
                    'message': 'Report generation completed',
                    'summary': {
                        'total_students': students.count(),
                        'reports_created': reports_created,
                        'reports_updated': reports_updated,
                        'errors': errors
                    },
                    'details': {
                        'term': term.display_name,
                        'class': classroom.name,
                        'exam': exam.name if exam else None,
                        'report_type': 'Exam Report' if exam else 'Term Summary'
                    }
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error in report publishing: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MyPublishedReportsView(APIView):
    """
    View for parents to get list of all published reports for their children
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all published reports for the parent's children"""
        try:
            if request.user.role != 'PARENT':
                return Response(
                    {'error': 'Access denied. Only parents can access this endpoint.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                parent_profile = request.user.parent_profile
                
                children_ids = parent_profile.children.values_list('id', flat=True)
                
                if not children_ids:
                    return Response({
                        'success': True,
                        'message': 'No children found for this parent',
                        'data': [],
                        'children': []
                    }, status=status.HTTP_200_OK)
                
                children = parent_profile.children.select_related('user')
                
                reports = Report.objects.filter(
                    student_id__in=children_ids,
                    is_published=True
                ).select_related(
                    'student__user', 
                    'term', 
                    'exam'
                ).order_by('-term__academic_year', 'term__name', 'student__admission_number')
                
                reports_data = []
                for report in reports:
                    reports_data.append({
                        'id': report.id,
                        'title': report.title,
                        'term_name': report.term.display_name,
                        'student_name': report.student.user.full_name,
                        'student_id': report.student.id,
                        'admission_number': report.student.admission_number,
                        'report_type': report.report_type,
                        'generated_at': report.generated_at.isoformat(),
                        'exam_name': report.exam.name if report.exam else None
                    })
                
                return Response({
                    'success': True,
                    'data': reports_data,
                    'children': [
                        {
                            'id': child.id,
                            'name': child.user.full_name,
                            'admission_number': child.admission_number
                        }
                        for child in children
                    ]
                }, status=status.HTTP_200_OK)
                
            except AttributeError:
                return Response({
                    'success': True,
                    'message': 'No parent profile found',
                    'data': [],
                    'children': []
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in MyPublishedReportsView: {str(e)}")
            return Response(
                {'error': 'An error occurred while fetching reports', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        
class AdminReportDetailView(APIView):
    """
    View for an Admin or Teacher to get the full report data for any report.
    This bypasses the parent-child ownership check.
    """
    permission_classes = [IsAdminOrTeacher]

    def get(self, request, pk=None):
        try:
            report = get_object_or_404(Report, pk=pk)
            
            if not report.is_published:
                return Response(
                    {'error': 'This report has not been published yet.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(report.report_data, status=status.HTTP_200_OK)

        except Report.DoesNotExist:
            return Response(
                {'error': 'Report not found.'},
                status=status.HTTP_44_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in AdminReportDetailView for report {pk}: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublishedReportDetailView(APIView):
    """
    View for a parent to get the full, stored JSON report data for a specific published report.
    """
    permission_classes = [IsParentUser]
    
    def get(self, request, pk=None):
        """Get full report data for a specific published report"""
        try:
            report = get_object_or_404(Report, pk=pk)
            
            try:
                parent_profile = request.user.parent_profile
                if report.student not in parent_profile.children.all():
                    return Response(
                        {'error': 'You do not have permission to view this report.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except AttributeError:
                return Response(
                    {'error': 'Parent profile not found.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not report.is_published:
                return Response(
                    {'error': 'This report has not been published yet.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(report.report_data, status=status.HTTP_200_OK)
            
        except Report.DoesNotExist:
            return Response(
                {'error': 'Report not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in PublishedReportDetailView for report {pk}: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred while fetching the report.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateSingleReportView(APIView):
    """Admin view to generate and publish a report card for a single student."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        student_id = request.data.get('student_id')
        term_id = request.data.get('term_id')

        if not student_id or not term_id:
            return Response({"error": "student_id and term_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = get_object_or_404(StudentProfile, id=student_id)
            term = get_object_or_404(Term, id=term_id)
            
            report_view = ReportCardDataView()
            report_data = report_view._generate_report_card_data(student, term, exam=None)
            
            title = f"{term.get_name_display()} {term.academic_year} - Term Report"
            
            report, created = Report.objects.update_or_create(
                student=student,
                term=term,
                exam=None, 
                defaults={
                    'title': title,
                    'report_data': report_data,
                    'is_published': True,
                    'generated_by': request.user,
                }
            )
            
            return Response({
                "success": True,
                "message": f"Report {'created' if created else 'updated'} for {student.user.full_name}",
                "report_id": report.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating single report: {str(e)}")
            return Response({"error": "Failed to generate report."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)