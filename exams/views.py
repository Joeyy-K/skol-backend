# exams/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Count, Avg, Max, Min, Q, Window, F, FloatField
from django.db.models.functions import Rank
from collections import Counter

from students.models import StudentProfile
from .models import Exam, StudentScore, Term
from .serializers import (
    ExamSerializer, StudentScoreSerializer, ExamStatisticsSerializer, TermSerializer
)
from auth_system.permissions import IsAdminOrTeacher, IsAdminOrOwner, IsAdminUser, IsParentUser
from rest_framework.generics import ListAPIView
from reports.models import Report
from django.http import HttpResponse
import csv

class TermViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing academic terms.
    """
    queryset = Term.objects.all().order_by('-academic_year', 'name')
    serializer_class = TermSerializer
    filterset_fields = ['academic_year', 'name', 'is_active']
    search_fields = ['name', 'academic_year']
    ordering_fields = ['academic_year', 'name', 'start_date', 'end_date']
    ordering = ['-academic_year', 'name']
    
    def get_permissions(self):
        """
        Assigns permissions based on action.
        - Admins can do anything.
        - Teachers can create and view.
        - Parents can only view.
        """
        if self.action in ['list', 'retrieve']:
            class CanViewTerms(IsAuthenticated):
                def has_permission(self, request, view):
                    return super().has_permission(request, view) and request.user.role in ['ADMIN', 'TEACHER', 'PARENT']
            return [CanViewTerms()]
        
        return [IsAdminOrTeacher()]
    
    @action(detail=False, methods=['get'])
    def current_terms(self, request):
        """Get currently active terms"""
        current_terms = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(current_terms, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_year(self, request):
        """Get terms grouped by academic year"""
        academic_year = request.query_params.get('year')
        if not academic_year:
            return Response(
                {'error': 'Academic year parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(academic_year)
            terms = self.queryset.filter(academic_year=year)
            serializer = self.get_serializer(terms, many=True)
            return Response({
                'academic_year': year,
                'terms': serializer.data,
                'count': terms.count()
            })
        except ValueError:
            return Response(
                {'error': 'Invalid academic year format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class ExamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing exams with custom actions for scores and statistics
    """
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['subject', 'classroom', 'term', 'date', 'term__academic_year']
    search_fields = ['name', 'subject__name', 'classroom__name', 'term__academic_year']
    ordering = ['-date', '-created_at']

    def get_permissions(self):
        """
        Assign permissions based on action.
        - Admins/Teachers can create and list exams.
        - Only the owner of the exam or an Admin can update or delete it.
        """
        if self.action in ['update', 'partial_update', 'destroy', 'add_scores']:
            permission_classes = [IsAdminOrOwner]
        elif self.action in ['list', 'retrieve', 'create', 'statistics', 'recent', 'get_scores']:
            permission_classes = [IsAdminOrTeacher]
        else:
            permission_classes = [IsAdminUser]
            
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_scores(self, request, pk=None):
        """
        Custom action to add/update student scores for an exam using update_or_create.
        Expects: {"scores": [{"student": 1, "score": 85.5, "remarks": "Good"}]}
        """
        exam = self.get_object()
        scores_data = request.data.get('scores', [])

        if not scores_data:
            return Response({'error': 'No scores data provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        successful_count = 0
        errors = []

        for score_data in scores_data:
            student_id = score_data.pop('student', None)
            if not student_id:
                errors.append({'data': score_data, 'error': 'student ID is missing.'})
                continue

            try:
                obj, created = StudentScore.objects.update_or_create(
                    exam=exam,
                    student_id=student_id,
                    defaults=score_data
                )
                successful_count += 1
            except Exception as e:
                errors.append({'student': student_id, 'error': str(e)})

        return Response({
            'message': f'Processed {len(scores_data)} scores.',
            'successful': successful_count,
            'failed': len(errors),
            'errors': errors
        })

    @action(detail=True, methods=['get'])
    def get_scores(self, request, pk=None):
        """
        Custom action to retrieve all scores for an exam
        """
        exam = self.get_object()
        scores = StudentScore.objects.filter(exam=exam).select_related('student')
        serializer = StudentScoreSerializer(scores, many=True)
        
        return Response({
            'exam': ExamSerializer(exam).data,
            'scores': serializer.data,
            'total_scores': scores.count()
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Custom action to get comprehensive statistics for an exam
        """
        exam = self.get_object()
        scores = StudentScore.objects.filter(exam=exam)
        
        if not scores.exists():
            return Response({
                'message': 'No scores available for this exam',
                'statistics': None
            })
        
        stats = scores.aggregate(
            total_students=Count('id'),
            average_score=Avg('score'),
            highest_score=Max('score'),
            lowest_score=Min('score')
        )
        
        pass_threshold = exam.max_score * 0.5
        pass_count = scores.filter(score__gte=pass_threshold).count()
        pass_rate = (pass_count / stats['total_students']) * 100 if stats['total_students'] > 0 else 0
        
        grades = [score.grade for score in scores]
        grade_distribution = dict(Counter(grades))
        
        statistics_data = {
            'total_students': stats['total_students'],
            'average_score': round(stats['average_score'], 2) if stats['average_score'] else 0,
            'highest_score': stats['highest_score'] or 0,
            'lowest_score': stats['lowest_score'] or 0,
            'pass_rate': round(pass_rate, 2),
            'grade_distribution': grade_distribution
        }
        
        serializer = ExamStatisticsSerializer(data=statistics_data)
        serializer.is_valid(raise_exception=True)
        
        return Response({
            'exam': {
                'id': exam.id,
                'name': exam.name,
                'subject': exam.subject.name,
                'classroom': exam.classroom.name,
                'max_score': exam.max_score
            },
            'statistics': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent exams (last 30 days)"""
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_exams = self.queryset.filter(date__gte=thirty_days_ago)
        
        page = self.paginate_queryset(recent_exams)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_exams, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='admin-gradebook')
    def admin_gradebook(self, request):
        class_id = request.query_params.get('class_id')
        term_id = request.query_params.get('term_id')

        if not class_id or not term_id:
            return Response({"error": "class_id and term_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        students = StudentProfile.objects.filter(classroom_id=class_id).select_related('user')

        published_reports_map = {
            report.student_id: report.id 
            for report in Report.objects.filter(
                student__in=students, 
                term_id=term_id, 
                is_published=True
            )
        }
        
        ranked_students = students.annotate(
            average_score=Avg(
                F('exam_scores__score') * 100.0 / F('exam_scores__exam__max_score'),
                filter=Q(exam_scores__exam__term_id=term_id),
                output_field=FloatField()
            ),
            rank=Window(
                expression=Rank(),
                order_by=F('average_score').desc(nulls_last=True)
            )
        ).order_by('rank', 'user__full_name')

        response_data = []
        for student in ranked_students:
            avg = student.average_score
            student_id = student.id
            is_published = student_id in published_reports_map

            response_data.append({
                'student_id': student_id,
                'full_name': student.user.full_name,
                'admission_number': student.admission_number,
                'average_score': round(avg, 2) if avg is not None else None,
                'rank': student.rank if avg is not None else None,
                'is_report_published': is_published,
                'report_id': published_reports_map.get(student_id) if is_published else None,
            })

        return Response(response_data)
    
    @action(detail=False, methods=['get'], url_path='download-gradebook-csv')
    def download_gradebook_csv(self, request):
        class_id = request.query_params.get('class_id')
        term_id = request.query_params.get('term_id')

        if not class_id or not term_id:
            return Response({"error": "class_id and term_id are required."}, status=400)

        students = StudentProfile.objects.filter(classroom_id=class_id).select_related('user')
        published_reports_map = { report.student_id: report.id for report in Report.objects.filter(student__in=students, term_id=term_id, is_published=True) }
        ranked_students = students.annotate(
            average_score=Avg(F('exam_scores__score') * 100.0 / F('exam_scores__exam__max_score'), filter=Q(exam_scores__exam__term_id=term_id), output_field=FloatField()),
            rank=Window(expression=Rank(), order_by=F('average_score').desc(nulls_last=True))
        ).order_by('rank', 'user__full_name')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="gradebook_class_{class_id}_term_{term_id}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Admission Number', 'Student Name', 'Average Score (%)', 'Class Rank', 'Report Status'])

        for student in ranked_students:
            avg = student.average_score
            status = 'Published' if student.id in published_reports_map else 'Not Published'
            writer.writerow([
                student.admission_number,
                student.user.full_name,
                round(avg, 2) if avg is not None else 'N/A',
                student.rank if avg is not None else 'N/A',
                status
            ])

        return response
    
class StudentScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual student scores
    """
    queryset = StudentScore.objects.all()
    serializer_class = StudentScoreSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['exam', 'student', 'exam__subject', 'exam__classroom', 'exam__term__academic_year']
    search_fields = ['student__first_name', 'student__last_name', 'exam__name']
    ordering = ['-exam__date', '-score']

class ClassGradebookView(ListAPIView):
    """
    Provides a comprehensive list of all exams and their scores for a specific class.
    Used by teachers to view the gradebook for their class.
    """
    serializer_class = ExamSerializer 
    permission_classes = [IsAdminOrTeacher]

    def get_queryset(self):
        """
        Filters exams based on the 'class_id' query parameter.
        """
        class_id = self.request.query_params.get('class_id', None)
        if not class_id:
            return Exam.objects.none() 

        if self.request.user.role == 'TEACHER':
            if not self.request.user.classes_in_charge.filter(pk=class_id).exists():
                return Exam.objects.none()
        
        return Exam.objects.filter(classroom_id=class_id).prefetch_related(
            'scores__student__user'
        ).order_by('-date')