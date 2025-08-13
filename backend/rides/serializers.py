from rest_framework import serializers
from .models import RideRequest, DriverAvailability
from accounts.serializers import UserSerializer

class DriverAvailabilitySerializer(serializers.ModelSerializer):
    driver = UserSerializer(read_only=True)

    class Meta:
        model = DriverAvailability
        fields = ('driver', 'is_available', 'current_lat', 'current_lon')

class RideRequestSerializer(serializers.ModelSerializer):
    rider = UserSerializer(read_only=True)
    driver = UserSerializer(read_only=True)

    class Meta:
        model = RideRequest
        fields = ('id', 'rider', 'driver', 'pickup_lat', 'pickup_lon', 'destination_lat', 'destination_lon', 'status', 'fare', 'distance')
        read_only_fields = ('rider', 'driver', 'status', 'fare', 'distance')
