from rest_framework import viewsets, permissions, status, mixins, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import django_filters.rest_framework

from .models import Job, JobCategory, JobApplication, ApplicationNote, AuditEvent
from .serializers import (
    JobSerializer, JobCategorySerializer, JobApplicationSerializer,
    ApplicationNoteSerializer
)
from .permissions import IsVipEmployer, IsJobOwner, IsApplicant, IsJobOwnerOfApplication
from .filters import JobFilter
from .utils import scan_file
from .notifications import send_new_application_notification, send_application_status_update_notification
from .throttling import JobApplicationRateThrottle


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    queryset = Job.objects.all().order_by('-created_at')
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = JobFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        # Public users only see published jobs
        if not user.is_authenticated or not user.is_staff:
            if self.action == 'list':
                queryset = queryset.filter(status='published')
        # Authenticated users see their own jobs regardless of status
        elif self.action == 'list':
             queryset = queryset.filter(status='published') | queryset.filter(employer=user)
        return queryset

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsVipEmployer]
        elif self.action in ['update', 'partial_update', 'destroy', 'publish', 'unpublish']:
            self.permission_classes = [IsVipEmployer, IsJobOwner]
        elif self.action == 'applications':
            self.permission_classes = [IsVipEmployer, IsJobOwner]
        else: # list, retrieve, apply
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(employer=self.request.user)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        job = self.get_object()
        if job.status == 'published':
            return Response({'detail': 'Job is already published.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = 'published'
        job.save()
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=['post'], url_path='unpublish')
    def unpublish(self, request, pk=None):
        job = self.get_object()
        if job.status != 'published':
            return Response({'detail': 'Job is not published.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = 'draft'
        job.save()
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], throttle_classes=[JobApplicationRateThrottle], url_path='apply')
    def apply(self, request, pk=None):
        job = self.get_object()
        if job.employer == request.user:
            return Response({'error': 'You cannot apply to your own job.'}, status=status.HTTP_400_BAD_REQUEST)
        if job.status != 'published':
            return Response({'error': 'This job is not open for applications.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = JobApplicationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            application = serializer.save(applicant=request.user, job=job, commit=False)
            try:
                application.full_clean()
            except ValidationError as e:
                return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

            if 'resume' in request.FILES:
                try:
                    scan_file(request.FILES['resume'])
                except ValidationError as e:
                    return Response({'error': e.messages}, status=status.HTTP_400_BAD_REQUEST)

            try:
                application.save()
                send_new_application_notification(application)
                AuditEvent.objects.create(
                    actor=request.user,
                    object_type='job_application',
                    object_id=application.id,
                    action='apply',
                    metadata={'job_id': job.id, 'job_title': job.title}
                )
                return Response(JobApplicationSerializer(application).data, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({'error': 'You have already applied for this job.'}, status=status.HTTP_409_CONFLICT)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        job = self.get_object()
        applications = job.applications.all()
        page = self.paginate_queryset(applications)
        if page is not None:
            serializer = JobApplicationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = JobApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class JobCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [permissions.AllowAny]


class MyJobApplicationsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JobApplication.objects.filter(applicant=self.request.user).order_by('-applied_at')


class JobApplicationManagementViewSet(mixins.RetrieveModelMixin,
                                      mixins.DestroyModelMixin,
                                      viewsets.GenericViewSet):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer

    def get_permissions(self):
        if self.action in ['retrieve', 'list_notes']:
            self.permission_classes = [permissions.IsAuthenticated, (IsApplicant | IsJobOwnerOfApplication | permissions.IsAdminUser)]
        elif self.action in ['change_status', 'add_note']:
            self.permission_classes = [permissions.IsAuthenticated, (IsJobOwnerOfApplication | permissions.IsAdminUser)]
        elif self.action == 'destroy':
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        application = self.get_object()
        status = request.data.get('status')
        if status not in ['shortlisted', 'rejected', 'hired']:
            return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        application.status = status
        application.save()
        send_application_status_update_notification(application)
        AuditEvent.objects.create(
            actor=request.user,
            object_type='job_application',
            object_id=application.id,
            action='status_change',
            metadata={'new_status': status}
        )
        return Response(JobApplicationSerializer(application).data)

    @action(detail=True, methods=['post'], url_path='notes')
    def add_note(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationNoteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            note = serializer.save(application=application, author=request.user)
            AuditEvent.objects.create(
                actor=request.user,
                object_type='application_note',
                object_id=note.id,
                action='note_added',
                metadata={'application_id': application.id}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='notes')
    def list_notes(self, request, pk=None):
        application = self.get_object()
        notes = application.notes.all()
        serializer = ApplicationNoteSerializer(notes, many=True)
        return Response(serializer.data)


import csv
from django.http import HttpResponse
import boto3
from botocore.exceptions import ClientError
from django.conf import settings


class ResumeDownloadView(generics.GenericAPIView):
    queryset = JobApplication.objects.all()
    permission_classes = [permissions.IsAuthenticated, (IsJobOwnerOfApplication | permissions.IsAdminUser)]

    def get(self, request, *args, **kwargs):
        application = self.get_object()

        if not application.resume:
            return Response({'error': 'No resume found for this application.'}, status=status.HTTP_404_NOT_FOUND)

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': application.resume.name},
                ExpiresIn=300 # 5 minutes
            )
        except ClientError:
            return Response({'error': 'Could not generate download URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'download_url': url})

class JobApplicationAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin ViewSet for managing all job applications.
    """
    queryset = JobApplication.objects.all().select_related('job', 'applicant').order_by('-applied_at')
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_fields = ['status', 'job', 'applicant']

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="job_applications.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Job Title', 'Applicant', 'Status', 'Applied At'])

        for app in self.get_queryset():
            writer.writerow([app.id, app.job.title, app.applicant.username, app.get_status_display(), app.applied_at])

        return response
