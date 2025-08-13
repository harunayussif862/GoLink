from rest_framework import serializers
from .models import RideRequest, DriverAvailability, Vehicle
from accounts.serializers import UserSerializer

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ('id', 'make', 'model', 'year', 'license_plate', 'ac_available', 'seats')

class DriverAvailabilitySerializer(serializers.ModelSerializer):
    driver = UserSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)

    class Meta:
        model = DriverAvailability
        fields = ('driver', 'vehicle', 'is_available', 'current_lat', 'current_lon')

class RideRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRequest
        fields = ('id', 'pickup_lat', 'pickup_lon', 'destination_lat', 'destination_lon')

class RideRequestEstimateSerializer(serializers.Serializer):
    pickup_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    pickup_lon = serializers.DecimalField(max_digits=9, decimal_places=6)
    destination_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    destination_lon = serializers.DecimalField(max_digits=9, decimal_places=6)
