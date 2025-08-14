from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobViewSet, JobCategoryViewSet, MyJobApplicationsViewSet,
    JobApplicationManagementViewSet, JobApplicationAdminViewSet, ResumeDownloadView
)

app_name = 'jobs'

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'job-categories', JobCategoryViewSet, basename='job-category')
router.register(r'my-applications', MyJobApplicationsViewSet, basename='my-job-application')
router.register(r'applications', JobApplicationManagementViewSet, basename='job-application-management')
router.register(r'admin/applications', JobApplicationAdminViewSet, basename='admin-job-application')


urlpatterns = [
    path('api/jobs/', include(router.urls)),
    path('api/jobs/applications/<int:pk>/resume/', ResumeDownloadView.as_view(), name='job-application-resume-download'),
]
