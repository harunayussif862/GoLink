from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Vehicle, PricingRule, DriverAvailability
from .services import calculate_fare
from decimal import Decimal

User = get_user_model()

class RideHailingTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.rider = User.objects.create_user(
            username='rider',
            email='rider@example.com',
            password='password'
        )
        cls.driver_user = User.objects.create_user(
            username='driver',
            email='driver@example.com',
            password='password',
            user_type='driver',
            is_role_verified=True
        )
        cls.vehicle = Vehicle.objects.create(
            driver=cls.driver_user,
            make='Toyota',
            model='Camry',
            year=2020,
            license_plate='GZ-1234-20',
            ac_available=True
        )
        cls.pricing_rule, _ = PricingRule.objects.get_or_create(name='Standard')
        cls.driver_availability = DriverAvailability.objects.create(
            driver=cls.driver_user,
            vehicle=cls.vehicle,
            is_available=True,
            current_lat=34.0522,
            current_lon=-118.2437
        )
        cls.fare_estimate_url = reverse('ride_hailing:fare_estimate')

    def test_pricing_service(self):
        """
        Test the dynamic pricing service.
        """
        fare = calculate_fare(
            distance=10,
            estimated_time=20,
            vehicle=self.vehicle,
            pricing_rule=self.pricing_rule
        )
        # (15 + (10 * 5) + (20 * 0.5)) * 1.2 = (15 + 50 + 10) * 1.2 = 75 * 1.2 = 90
        self.assertEqual(fare, Decimal('90.00'))

    def test_fare_estimate_api(self):
        """
        Test the fare estimate API endpoint.
        """
        self.client.force_authenticate(user=self.rider)
        data = {
            'pickup_lat': 34.0522,
            'pickup_lon': -118.2437,
            'destination_lat': 34.0522,
            'destination_lon': -118.2437,
        }
        response = self.client.post(self.fare_estimate_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn('estimated_fare', response.data[0])
        # (15 + (10.5 * 5) + (25 * 0.5)) * 1.2 = (15 + 52.5 + 12.5) * 1.2 = 80 * 1.2 = 96
        self.assertEqual(response.data[0]['estimated_fare'], Decimal('96.00'))
