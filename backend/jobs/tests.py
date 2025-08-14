from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import RoleForm, RoleApplication
import json

User = get_user_model()

class VIPEmployerApplicationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a regular user who will apply to be a VIP employer
        cls.applicant_user = User.objects.create_user(
            username='vip_applicant',
            email='vip_applicant@example.com',
            password='testpassword'
        )

        # Create an admin user to approve the application
        cls.admin_user = User.objects.create_superuser(
            username='admin_jobs',
            email='admin_jobs@example.com',
            password='adminpassword'
        )

        # Get the VIP Employer form created by the migration
        try:
            cls.vip_form = RoleForm.objects.get(role='vip_employer')
        except RoleForm.DoesNotExist:
            # If the migration hasn't run in the test DB setup, create it
            cls.vip_form = RoleForm.objects.create(
                name='VIP Employer Application',
                role='vip_employer'
            )


    def setUp(self):
        self.apply_url = reverse('accounts:role_apply')
        self.admin_list_url = reverse('accounts:admin_roles-list')

    def test_user_can_apply_for_vip_employer(self):
        """
        Ensure a user can successfully submit an application for the VIP Employer role.
        """
        self.client.force_authenticate(user=self.applicant_user)

        # Create dummy files for the application
        doc1 = SimpleUploadedFile("company_reg.pdf", b"file_content_1", content_type="application/pdf")
        doc2 = SimpleUploadedFile("tax_id.pdf", b"file_content_2", content_type="application/pdf")
        logo = SimpleUploadedFile("logo.png", b"logo_content", content_type="image/png")
        selfie = SimpleUploadedFile("selfie.jpg", b"selfie_content", content_type="image/jpeg")

        form_data = {
            'I agree to the VIP Employer Terms & Conditions': True,
        }

        data = {
            'role_form': self.vip_form.id,
            'form_data': json.dumps(form_data),
            'Company Registration Documents': doc1,
            'Business License or Tax ID': doc2,
            'Logo/Branding Assets': logo,
            'Selfie of Company Representative with Valid ID': selfie,
        }

        response = self.client.post(self.apply_url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RoleApplication.objects.count(), 1)
        application = RoleApplication.objects.first()
        self.assertEqual(application.user, self.applicant_user)
        self.assertEqual(application.role_form, self.vip_form)
        self.assertEqual(application.files.count(), 4)
        self.assertTrue(application.form_data['I agree to the VIP Employer Terms & Conditions'])

    def test_admin_can_approve_vip_employer_application(self):
        """
        Ensure an admin can approve a VIP employer application and the user's role is updated.
        """
        # First, create an application
        application = RoleApplication.objects.create(
            user=self.applicant_user,
            role_form=self.vip_form,
            form_data={'I agree': True}
        )

        self.client.force_authenticate(user=self.admin_user)

        approval_url = reverse('accounts:admin_roles-detail', kwargs={'pk': application.pk})
        data = {'status': 'approved'}

        response = self.client.patch(approval_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user from DB and check their status
        self.applicant_user.refresh_from_db()
        self.assertEqual(self.applicant_user.user_type, 'job_poster')
        self.assertTrue(self.applicant_user.is_vip_employer)
        self.assertTrue(self.applicant_user.is_role_verified)

    def test_admin_can_reject_vip_employer_application(self):
        """
        Ensure an admin can reject a VIP employer application.
        """
        application = RoleApplication.objects.create(
            user=self.applicant_user,
            role_form=self.vip_form,
            form_data={'I agree': True}
        )

        self.client.force_authenticate(user=self.admin_user)

        rejection_url = reverse('accounts:admin_roles-detail', kwargs={'pk': application.pk})
        data = {'status': 'rejected'}

        response = self.client.patch(rejection_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.applicant_user.refresh_from_db()
        self.assertNotEqual(self.applicant_user.user_type, 'job_poster')
        self.assertFalse(self.applicant_user.is_vip_employer)
        self.assertFalse(self.applicant_user.is_role_verified)


from .models import Job, JobCategory

class JobPostingAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.vip_employer = User.objects.create_user(
            username='vip_employer',
            email='vip_employer@example.com',
            password='testpassword',
            is_vip_employer=True,
            is_role_verified=True,
            user_type='job_poster'
        )
        cls.normal_user = User.objects.create_user(
            username='normal_user',
            email='normal@example.com',
            password='testpassword'
        )
        cls.category = JobCategory.objects.create(name='Engineering')

    def setUp(self):
        self.jobs_url = reverse('jobs:job-list')
        self.client.force_authenticate(user=self.vip_employer)

    def test_vip_employer_can_create_job(self):
        data = {
            'title': 'Senior Developer',
            'description': 'A job for a senior dev.',
            'job_type': 'full-time',
            'category_id': self.category.id
        }
        response = self.client.post(self.jobs_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(Job.objects.first().employer, self.vip_employer)

    def test_normal_user_cannot_create_job(self):
        self.client.force_authenticate(user=self.normal_user)
        data = {'title': 'Job by normal user', 'description': 'desc', 'job_type': 'part-time'}
        response = self.client.post(self.jobs_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_edit_job(self):
        job = Job.objects.create(employer=self.vip_employer, title='Old Title', description='..', job_type='full-time')
        detail_url = reverse('jobs:job-detail', kwargs={'pk': job.pk})
        data = {'title': 'New Title'}
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.title, 'New Title')

    def test_non_owner_cannot_edit_job(self):
        another_vip = User.objects.create_user(username='another_vip', password='p', is_vip_employer=True)
        job = Job.objects.create(employer=another_vip, title='A Job', description='..', job_type='full-time')
        self.client.force_authenticate(user=self.vip_employer)
        detail_url = reverse('jobs:job-detail', kwargs={'pk': job.pk})
        data = {'title': 'New Title'}
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_publish_unpublish_flow(self):
        job = Job.objects.create(employer=self.vip_employer, title='A Job', status='draft', job_type='full-time')
        publish_url = reverse('jobs:job-publish', kwargs={'pk': job.pk})
        unpublish_url = reverse('jobs:job-unpublish', kwargs={'pk': job.pk})

        # Publish
        response = self.client.post(publish_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, 'published')

        # Unpublish
        response = self.client.post(unpublish_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, 'draft')

    def test_public_list_shows_only_published_jobs(self):
        Job.objects.create(employer=self.vip_employer, title='Published Job', status='published', job_type='full-time')
        Job.objects.create(employer=self.vip_employer, title='Draft Job', status='draft', job_type='full-time')

        self.client.logout()
        response = self.client.get(self.jobs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Published Job')

    def test_filtering_jobs(self):
        Job.objects.create(employer=self.vip_employer, title='Dev in NY', status='published', job_type='full-time', location='New York')
        Job.objects.create(employer=self.vip_employer, title='Dev in SF', status='published', job_type='full-time', location='San Francisco')
        Job.objects.create(employer=self.vip_employer, title='Designer in NY', status='published', job_type='part-time', location='New York')

        self.client.logout()

        # Filter by location
        response = self.client.get(self.jobs_url + '?location=New York')
        self.assertEqual(len(response.data['results']), 2)

        # Filter by job_type
        response = self.client.get(self.jobs_url + '?job_type=part-time')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Designer in NY')

    def test_apply_stub(self):
        job = Job.objects.create(employer=self.vip_employer, title='A Job', status='published', job_type='full-time')
        apply_url = reverse('jobs:job-apply', kwargs={'pk': job.pk})
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.post(apply_url)
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
