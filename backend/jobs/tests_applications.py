from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Job, JobCategory, JobApplication
from unittest.mock import patch

User = get_user_model()

class JobApplicationAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.employer = User.objects.create_user(username='employer', password='p', is_vip_employer=True, user_type='job_poster', is_role_verified=True)
        cls.applicant = User.objects.create_user(username='applicant', password='p')
        cls.other_user = User.objects.create_user(username='other', password='p')
        cls.admin = User.objects.create_superuser(username='admin', password='p')

        cls.job = Job.objects.create(employer=cls.employer, title='Test Job', description='Desc', job_type='full-time', status='published')

    def test_apply_success(self):
        self.client.force_authenticate(user=self.applicant)
        resume = SimpleUploadedFile("resume.pdf", b"file_content", content_type="application/pdf")
        data = {'cover_letter': 'My cover letter.', 'resume': resume}

        with patch('jobs.views.send_new_application_notification') as mock_notify:
            response = self.client.post(reverse('jobs:job-apply', kwargs={'pk': self.job.pk}), data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(JobApplication.objects.count(), 1)
            mock_notify.assert_called_once()

    def test_apply_to_own_job_fails(self):
        self.client.force_authenticate(user=self.employer)
        response = self.client.post(reverse('jobs:job-apply', kwargs={'pk': self.job.pk}), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_twice_fails(self):
        JobApplication.objects.create(job=self.job, applicant=self.applicant, cover_letter='first')
        self.client.force_authenticate(user=self.applicant)
        data = {'cover_letter': 'second', 'resume': SimpleUploadedFile("r.pdf", b"c")}
        response = self.client.post(reverse('jobs:job-apply', kwargs={'pk': self.job.pk}), data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_applicant_can_list_own_applications(self):
        JobApplication.objects.create(job=self.job, applicant=self.applicant, cover_letter='...')
        self.client.force_authenticate(user=self.applicant)
        response = self.client.get(reverse('jobs:my-job-application-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_employer_can_list_applications_for_own_job(self):
        JobApplication.objects.create(job=self.job, applicant=self.applicant, cover_letter='...')
        self.client.force_authenticate(user=self.employer)
        response = self.client.get(reverse('jobs:job-applications', kwargs={'pk': self.job.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_employer_cannot_list_applications_for_other_job(self):
        other_employer = User.objects.create_user(username='other_emp', password='p', is_vip_employer=True)
        other_job = Job.objects.create(employer=other_employer, title='Other Job', job_type='full-time', status='published')
        JobApplication.objects.create(job=other_job, applicant=self.applicant, cover_letter='...')

        self.client.force_authenticate(user=self.employer)
        response = self.client.get(reverse('jobs:job-applications', kwargs={'pk': other_job.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employer_can_change_status(self):
        app = JobApplication.objects.create(job=self.job, applicant=self.applicant, cover_letter='...')
        self.client.force_authenticate(user=self.employer)
        url = reverse('jobs:job-application-management-change-status', kwargs={'pk': app.pk})

        with patch('jobs.views.send_application_status_update_notification') as mock_notify:
            response = self.client.patch(url, {'status': 'shortlisted'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            app.refresh_from_db()
            self.assertEqual(app.status, 'shortlisted')
            mock_notify.assert_called_once()

    def test_resume_download_permissions(self):
        app = JobApplication.objects.create(job=self.job, applicant=self.applicant, cover_letter='...')
        url = reverse('jobs:job-application-resume-download', kwargs={'pk': app.pk})

        # Deny applicant
        self.client.force_authenticate(user=self.applicant)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Allow job owner
        self.client.force_authenticate(user=self.employer)
        with patch('jobs.views.boto3.client') as mock_boto:
            mock_s3 = mock_boto.return_value
            mock_s3.generate_presigned_url.return_value = "http://s3.signed/url"
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('download_url', response.data)
