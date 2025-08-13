from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import DriverAvailability, RideRequest
from .services import calculate_fare
from decimal import Decimal

User = get_user_model()

class RideAPITests(APITestCase):

    def setUp(self):
        self.rider = User.objects.create_user(
            username='rider',
            email='rider@example.com',
            password='password'
        )
        self.driver_user = User.objects.create_user(
            username='driver',
            email='driver@example.com',
            password='password',
            user_type='driver',
            is_role_verified=True
        )
        self.driver_availability = DriverAvailability.objects.create(
            driver=self.driver_user,
            is_available=True,
            current_lat=34.0522,
            current_lon=-118.2437
        )
        self.ride_request_url = reverse('rides:ride_request')
        self.driver_availability_url = reverse('rides:driver_availability')

    def test_calculate_fare(self):
        """
        Test the fare calculation logic.
        """
        fare = calculate_fare(distance=10)
        self.assertEqual(fare, Decimal('65.00')) # 15 + (10 * 5)

        fare_ac = calculate_fare(distance=10, ac_enabled=True)
        self.assertEqual(fare_ac, Decimal('78.00')) # 65 * 1.2

        fare_premium = calculate_fare(distance=10, vehicle_type='premium')
        self.assertEqual(fare_premium, Decimal('97.50')) # 65 * 1.5

    def test_driver_availability(self):
        """
        Test updating driver availability.
        """
        self.client.force_authenticate(user=self.driver_user)
        data = {'is_available': False}
        response = self.client.put(self.driver_availability_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.driver_availability.refresh_from_db()
        self.assertFalse(self.driver_availability.is_available)

    def test_ride_request(self):
        """
        Test creating a ride request.
        """
        self.client.force_authenticate(user=self.rider)
        data = {
            'pickup_lat': 34.0522,
            'pickup_lon': -118.2437,
            'destination_lat': 34.0522,
            'destination_lon': -118.2437,
        }
        response = self.client.post(self.ride_request_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RideRequest.objects.count(), 1)
        ride = RideRequest.objects.first()
        self.assertEqual(ride.rider, self.rider)
        self.assertIn('available_drivers', response.data)
        self.assertEqual(len(response.data['available_drivers']), 1)
