from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import DriverAvailability
from .serializers import RideRequestEstimateSerializer, DriverAvailabilitySerializer
from .services import calculate_fare, get_active_pricing_rule
from decimal import Decimal
import json

class FareEstimateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RideRequestEstimateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Mock distance and time calculation
        distance = Decimal('10.5') # In a real app, this would be calculated using a mapping service
        estimated_time = 25 # in minutes

        pricing_rule = get_active_pricing_rule()
        if not pricing_rule:
            return Response({'error': 'No active pricing rule found'}, status=status.HTTP_400_BAD_REQUEST)

        # Find available drivers (simplified)
        available_drivers = DriverAvailability.objects.filter(is_available=True, vehicle__isnull=False)

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
