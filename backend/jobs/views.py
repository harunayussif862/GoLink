from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Job, JobCategory
from .serializers import JobSerializer, JobCategorySerializer
from .permissions import IsVipEmployer, IsJobOwner
from .filters import JobFilter
import django_filters.rest_framework

class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    queryset = Job.objects.all().order_by('-created_at')
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = JobFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-authenticated or non-staff users should only see published jobs
        if not self.request.user.is_authenticated or not self.request.user.is_staff:
             if self.action == 'list':
                queryset = queryset.filter(status='published')
        return queryset

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            self.permission_classes = [IsVipEmployer]
        elif self.action in ['update', 'partial_update', 'destroy', 'publish', 'unpublish']:
            self.permission_classes = [IsVipEmployer, IsJobOwner]
        else: # list, retrieve
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='apply')
    def apply(self, request, pk=None):
        return Response({'detail': 'Coming soon'}, status=status.HTTP_501_NOT_IMPLEMENTED)

class JobCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [permissions.AllowAny]
