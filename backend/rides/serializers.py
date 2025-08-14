from rest_framework import serializers
from .models import RideRequest, DriverAvailability, Vehicle, Review, Report
from accounts.serializers import UserSerializer

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ('id', 'make', 'model', 'year', 'license_plate', 'ac_available', 'seats', 'vehicle_tier')

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

class FareEstimateSerializer(serializers.Serializer):
    pickup_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    pickup_lon = serializers.DecimalField(max_digits=9, decimal_places=6)
    destination_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    destination_lon = serializers.DecimalField(max_digits=9, decimal_places=6)
    vehicle_tier = serializers.ChoiceField(choices=Vehicle.VEHICLE_TIER_CHOICES)

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'ride', 'rating', 'comment', 'created_at')
        read_only_fields = ('reviewer', 'reviewed')

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ('id', 'ride', 'reason', 'description', 'created_at')
        read_only_fields = ('reporter',)
