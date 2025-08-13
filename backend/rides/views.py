from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import RideRequest, DriverAvailability
from .serializers import RideRequestSerializer, DriverAvailabilitySerializer
from .services import calculate_fare
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

class DriverAvailabilityView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DriverAvailabilitySerializer

    def get_object(self):
        # Limit choices to driver
        if self.request.user.user_type != 'driver':
            return None
        obj, created = DriverAvailability.objects.get_or_create(driver=self.request.user)
        return obj

class RideRequestView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RideRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Mock distance calculation
        distance = Decimal('10.5') # In a real app, this would be calculated using a mapping service

        # Calculate fare
        fare = calculate_fare(distance)

        # Find available drivers (simplified)
        available_drivers = DriverAvailability.objects.filter(is_available=True)
        if not available_drivers.exists():
            return Response({'error': 'No available drivers at the moment'}, status=status.HTTP_404_NOT_FOUND)

        # For simplicity, we are not assigning a driver here.
        # This will be handled in the ride acceptance flow.

        ride_request = serializer.save(
            rider=request.user,
            distance=distance,
            fare=fare
        )

        # Prepare response
        response_data = serializer.data
        response_data['available_drivers'] = DriverAvailabilitySerializer(available_drivers, many=True).data

        return Response(response_data, status=status.HTTP_201_CREATED)
