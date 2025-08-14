from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Job, JobCategory, FeaturedPricing
from wallets.models import Wallet
from unittest.mock import patch

User = get_user_model()

class FeaturedJobAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.standard_employer = User.objects.create_user(username='standard', password='p', user_type='job_poster', is_role_verified=True)
        cls.vip_employer = User.objects.create_user(username='vip', password='p', user_type='job_poster', is_role_verified=True, is_vip_employer=True)
        cls.admin = User.objects.create_superuser(username='admin', password='p')

        # Setup wallets
        cls.standard_wallet = Wallet.objects.get(user=cls.standard_employer)
        cls.standard_wallet.balance = 1000
        cls.standard_wallet.save()

        cls.vip_wallet = Wallet.objects.get(user=cls.vip_employer)
        cls.vip_wallet.balance = 1000
        cls.vip_wallet.save()

        # Setup pricing
        FeaturedPricing.objects.create(price_per_day=10, min_days=1, max_days=30)

    def test_standard_employer_job_pending_review(self):
        self.client.force_authenticate(user=self.standard_employer)
        data = {'title': 'Standard Job', 'description': 'desc', 'job_type': 'full-time'}
        response = self.client.post(reverse('jobs:job-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = Job.objects.get(pk=response.data['id'])
        self.assertEqual(job.status, 'pending_review')

    def test_vip_employer_job_published(self):
        self.client.force_authenticate(user=self.vip_employer)
        data = {'title': 'VIP Job', 'description': 'desc', 'job_type': 'full-time'}
        response = self.client.post(reverse('jobs:job-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = Job.objects.get(pk=response.data['id'])
        self.assertEqual(job.status, 'published')

    def test_admin_can_approve_job(self):
        job = Job.objects.create(employer=self.standard_employer, title='A Job', status='pending_review', job_type='full-time')
        self.client.force_authenticate(user=self.admin)
        url = reverse('jobs:admin-job-approve', kwargs={'pk': job.pk})

        with patch('jobs.views.send_job_status_update_notification') as mock_notify:
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            job.refresh_from_db()
            self.assertEqual(job.status, 'published')
            mock_notify.assert_called_once()

    def test_feature_job_success(self):
        job = Job.objects.create(employer=self.vip_employer, title='A Job', status='published', job_type='full-time')
        self.client.force_authenticate(user=self.vip_employer)
        url = reverse('jobs:job-feature', kwargs={'pk': job.pk})

        with patch('jobs.views.send_job_featured_notification') as mock_notify:
            response = self.client.post(url, {'days': 10}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            job.refresh_from_db()
            self.assertTrue(job.is_featured)
            self.assertIsNotNone(job.featured_until)
            self.vip_wallet.refresh_from_db()
            self.assertEqual(self.vip_wallet.balance, 900)
            mock_notify.assert_called_once()

    def test_feature_job_insufficient_balance(self):
        job = Job.objects.create(employer=self.vip_employer, title='A Job', status='published', job_type='full-time')
        self.vip_wallet.balance = 50
        self.vip_wallet.save()
        self.client.force_authenticate(user=self.vip_employer)
        url = reverse('jobs:job-feature', kwargs={'pk': job.pk})
        response = self.client.post(url, {'days': 10}, format='json')
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_public_list_prioritizes_featured(self):
        featured_job = Job.objects.create(employer=self.vip_employer, title='Featured Job', status='published', job_type='full-time', is_featured=True, featured_until=timezone.now() + timedelta(days=1))
        normal_job = Job.objects.create(employer=self.vip_employer, title='Normal Job', status='published', job_type='full-time')

        self.client.logout()
        response = self.client.get(reverse('jobs:job-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['title'], 'Featured Job')
        self.assertEqual(response.data['results'][1]['title'], 'Normal Job')
