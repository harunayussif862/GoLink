import pytest
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Vehicle, PricingRule, DriverAvailability, RideRequest, Review, Report
from .services import calculate_fare
from decimal import Decimal
from wallets.models import Wallet
from channels.testing import WebsocketCommunicator
from .consumers import RideLocationConsumer
from golink.asgi import application

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
        cls.vip_driver_user = User.objects.create_user(
            username='vip_driver',
            email='vip_driver@example.com',
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
            ac_available=True,
            vehicle_tier='standard'
        )
        cls.vip_vehicle = Vehicle.objects.create(
            driver=cls.vip_driver_user,
            make='Mercedes',
            model='S-Class',
            year=2022,
            license_plate='GZ-5678-22',
            ac_available=True,
            vehicle_tier='vip'
        )
        cls.pricing_rule, _ = PricingRule.objects.get_or_create(name='Standard')
        cls.driver_availability = DriverAvailability.objects.create(
            driver=cls.driver_user,
            vehicle=cls.vehicle,
            is_available=True,
            current_lat=34.0522,
            current_lon=-118.2437
        )
        cls.vip_driver_availability = DriverAvailability.objects.create(
            driver=cls.vip_driver_user,
            vehicle=cls.vip_vehicle,
            is_available=True,
            current_lat=34.0522,
            current_lon=-118.2437
        )
        cls.fare_estimate_url = reverse('rides:fare_estimate')

    def test_pricing_service(self):
        """
        Test the dynamic pricing service with different tiers.
        """
        # Standard
        fare_standard = calculate_fare(distance=10, estimated_time=20, vehicle=self.vehicle, pricing_rule=self.pricing_rule)
        self.assertEqual(fare_standard, Decimal('90.00')) # (15 + 10*5 + 20*0.5) * 1.2

        # VIP
        fare_vip = calculate_fare(distance=10, estimated_time=20, vehicle=self.vip_vehicle, pricing_rule=self.pricing_rule)
        self.assertEqual(fare_vip, Decimal('270.00')) # (15 + 10*5 + 20*0.5) * 3.0

    def test_fare_estimate_api(self):
        """
        Test the fare estimate API endpoint with different tiers.
        """
        self.client.force_authenticate(user=self.rider)

        # Standard tier
        data_standard = {'pickup_lat': 34.0522, 'pickup_lon': -118.2437, 'destination_lat': 34.0522, 'destination_lon': -118.2437, 'vehicle_tier': 'standard'}
        response_standard = self.client.post(self.fare_estimate_url, data_standard, format='json')
        self.assertEqual(response_standard.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_standard.data), 1)
        self.assertEqual(response_standard.data[0]['vehicle']['vehicle_tier'], 'standard')

        # VIP tier
        data_vip = {'pickup_lat': 34.0522, 'pickup_lon': -118.2437, 'destination_lat': 34.0522, 'destination_lon': -118.2437, 'vehicle_tier': 'vip'}
        response_vip = self.client.post(self.fare_estimate_url, data_vip, format='json')
        self.assertEqual(response_vip.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_vip.data), 1)
        self.assertEqual(response_vip.data[0]['vehicle']['vehicle_tier'], 'vip')


class RideLifecycleAPITests(APITestCase):

    def setUp(self):
        self.rider = User.objects.create_user(username='rider', email='rider@example.com', password='password')
        self.driver = User.objects.create_user(username='driver', email='driver@example.com', password='password', user_type='driver', is_role_verified=True)
        self.rider_wallet = Wallet.objects.get(user=self.rider)
        self.rider_wallet.balance = 500
        self.rider_wallet.save()
        self.ride = RideRequest.objects.create(
            rider=self.rider,
            pickup_lat=34.0522,
            pickup_lon=-118.2437,
            destination_lat=34.0522,
            destination_lon=-118.2437,
            fare=100.00
        )

    def test_accept_ride(self):
        """
        Ensure a driver can accept a ride request.
        """
        self.client.force_authenticate(user=self.driver)
        url = reverse('rides:rides-accept', kwargs={'pk': self.ride.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, 'accepted')
        self.assertEqual(self.ride.driver, self.driver)

    def test_start_ride(self):
        """
        Ensure a driver can start an accepted ride.
        """
        self.ride.driver = self.driver
        self.ride.status = 'accepted'
        self.ride.save()
        self.client.force_authenticate(user=self.driver)
        url = reverse('rides:rides-start', kwargs={'pk': self.ride.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, 'in_progress')

    def test_end_ride(self):
        """
        Ensure a driver can end a ride and payment is processed.
        """
        self.ride.driver = self.driver
        self.ride.status = 'in_progress'
        self.ride.save()
        self.client.force_authenticate(user=self.driver)
        # Create GoLink platform user for commission
        User.objects.create_superuser(username='golink_platform', email='platform@golink.com', password='password')
        url = reverse('rides:rides-end', kwargs={'pk': self.ride.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, 'completed')

        self.rider_wallet.refresh_from_db()
        self.assertEqual(self.rider_wallet.balance, 400) # 500 - 100

        driver_wallet = Wallet.objects.get(user=self.driver)
        self.assertEqual(driver_wallet.balance, 85) # 100 - 15 (15% commission)


class RideFeedbackAPITests(APITestCase):

    def setUp(self):
        self.rider = User.objects.create_user(username='rider', email='rider@example.com', password='password')
        self.driver = User.objects.create_user(username='driver', email='driver@example.com', password='password', user_type='driver', is_role_verified=True)
        self.ride = RideRequest.objects.create(
            rider=self.rider,
            driver=self.driver,
            status='completed',
            fare=100.00
        )

    def test_create_review(self):
        """
        Ensure a user can create a review for a completed ride.
        """
        self.client.force_authenticate(user=self.rider)
        url = reverse('rides:ride-reviews-list', kwargs={'ride_pk': self.ride.pk})
        data = {'rating': 5, 'comment': 'Great ride!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        review = Review.objects.first()
        self.assertEqual(review.reviewer, self.rider)
        self.assertEqual(review.reviewed, self.driver)

    def test_create_report(self):
        """
        Ensure a user can create a report for a ride.
        """
        self.client.force_authenticate(user=self.rider)
        url = reverse('rides:ride-reports-list', kwargs={'ride_pk': self.ride.pk})
        data = {'reason': 'Driver was rude'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.reporter, self.rider)


@pytest.mark.asyncio
class RideLocationConsumerTests(APITestCase):

    async def test_ride_location_consumer(self):
        ride = RideRequest.objects.create(
            rider=User.objects.create_user(username='rider_consumer', email='rider_consumer@example.com', password='password'),
            pickup_lat=34.0522,
            pickup_lon=-118.2437,
            destination_lat=34.0522,
            destination_lon=-118.2437,
        )
        communicator = WebsocketCommunicator(application, f"/ws/rides/{ride.id}/location/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Test sending a location update
        await communicator.send_json_to({'lat': 34.0522, 'lon': -118.2437})
        response = await communicator.receive_json_from()
        self.assertEqual(response['lat'], 34.0522)
        self.assertEqual(response['lon'], -118.2437)

        # Close the connection
        await communicator.disconnect()
