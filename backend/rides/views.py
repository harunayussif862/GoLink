from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction, models
from .models import RideRequest, DriverAvailability, Review, Report
from .serializers import RideRequestSerializer, DriverAvailabilitySerializer, FareEstimateSerializer, ReviewSerializer, ReportSerializer
from .services import calculate_fare, get_active_pricing_rule
from wallets.models import Wallet
from wallets.utils import handle_commission
from decimal import Decimal

class DriverAvailabilityView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DriverAvailabilitySerializer

    def get_object(self):
        if self.request.user.user_type != 'driver':
            return None
        obj, created = DriverAvailability.objects.get_or_create(driver=self.request.user)
        return obj

class FareEstimateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FareEstimateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Mock distance and time calculation
        distance = Decimal('10.5')
        estimated_time = 25

        pricing_rule = get_active_pricing_rule()
        if not pricing_rule:
            return Response({'error': 'No active pricing rule found'}, status=status.HTTP_400_BAD_REQUEST)

        available_drivers = DriverAvailability.objects.filter(
            is_available=True,
            vehicle__isnull=False,
            vehicle__vehicle_tier=data['vehicle_tier']
        )

        response_data = []
        for availability in available_drivers:
            fare = calculate_fare(
                distance=distance,
                estimated_time=estimated_time,
                vehicle=availability.vehicle,
                pricing_rule=pricing_rule
            )
            driver_data = DriverAvailabilitySerializer(availability).data
            driver_data['estimated_fare'] = fare
            response_data.append(driver_data)

        return Response(response_data, status=status.HTTP_200_OK)

class RideRequestViewSet(viewsets.ModelViewSet):
    serializer_class = RideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return RideRequest.objects.all()
        if user.user_type == 'driver':
            # A driver can see rides they have accepted, or pending rides to accept.
            # This is a simplified logic. In a real app, a driver would only see
            # rides that have been offered to them.
            return RideRequest.objects.filter(models.Q(driver=user) | models.Q(status='pending'))
        return RideRequest.objects.filter(rider=user)

    def perform_create(self, serializer):
        # In a real app, the driver would be assigned after they accept the request.
        # For now, we allow passing the driver in the request for testing purposes.
        serializer.save(rider=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        ride = self.get_object()
        if ride.status != 'pending' or ride.driver is not None:
            return Response({'error': 'Ride cannot be accepted'}, status=status.HTTP_400_BAD_REQUEST)

        driver = request.user
        if driver.user_type != 'driver':
            return Response({'error': 'You are not a driver'}, status=status.HTTP_403_FORBIDDEN)

        ride.driver = driver
        ride.status = 'accepted'
        ride.accepted_at = timezone.now()
        ride.save()
        return Response(self.get_serializer(ride).data)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(ride_id=self.kwargs['ride_pk'])

    def perform_create(self, serializer):
        ride = RideRequest.objects.get(pk=self.kwargs['ride_pk'])
        reviewed_user = ride.driver if self.request.user == ride.rider else ride.rider
        serializer.save(reviewer=self.request.user, reviewed=reviewed_user, ride=ride)

class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(ride_id=self.kwargs['ride_pk'])

    def perform_create(self, serializer):
        ride = RideRequest.objects.get(pk=self.kwargs['ride_pk'])
        serializer.save(reporter=self.request.user, ride=ride)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        ride = self.get_object()
        if ride.status != 'accepted' or ride.driver != request.user:
            return Response({'error': 'Ride cannot be started'}, status=status.HTTP_400_BAD_REQUEST)

        ride.status = 'in_progress'
        ride.started_at = timezone.now()
        ride.save()
        return Response(self.get_serializer(ride).data)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        ride = self.get_object()
        if ride.status != 'in_progress' or ride.driver != request.user:
            return Response({'error': 'Ride cannot be ended'}, status=status.HTTP_400_BAD_REQUEST)

        ride.status = 'completed'
        ride.completed_at = timezone.now()

        with transaction.atomic():
            rider_wallet = Wallet.objects.get(user=ride.rider)
            driver_wallet = Wallet.objects.get(user=ride.driver)

            if rider_wallet.balance < ride.fare:
                # In a real app, we might charge a card on file or handle this differently
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

            rider_wallet.balance -= ride.fare
            rider_wallet.save()

            driver_wallet.balance += ride.fare
            driver_wallet.save()

            # Handle commission
            commission_rate = Decimal('0.15') # 15% commission
            handle_commission(driver_wallet, ride.fare, commission_rate)

            ride.save()

        return Response(self.get_serializer(ride).data)
