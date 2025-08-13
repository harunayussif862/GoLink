from django.db import models
from django.conf import settings

class Vehicle(models.Model):
    VEHICLE_TIER_CHOICES = (
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
    )
    driver = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'user_type': 'driver'})
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    license_plate = models.CharField(max_length=20, unique=True)
    ac_available = models.BooleanField(default=False)
    seats = models.PositiveIntegerField(default=4)
    vehicle_tier = models.CharField(max_length=20, choices=VEHICLE_TIER_CHOICES, default='standard')

    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"

class PricingRule(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=15.00)
    per_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    per_minute_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.50)
    ac_surcharge = models.DecimalField(max_digits=5, decimal_places=2, default=1.2) # 20%
    premium_tier_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.5) # 50%
    vip_tier_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=3.0) # 300%
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class DriverAvailability(models.Model):
    driver = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'user_type': 'driver'})
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    is_available = models.BooleanField(default=False)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.driver.username} - {'Available' if self.is_available else 'Unavailable'}"

class RideRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ride_requests')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver', limit_choices_to={'user_type': 'driver'})

    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lon = models.DecimalField(max_digits=9, decimal_places=6)
    destination_lat = models.DecimalField(max_digits=9, decimal_places=6)
    destination_lon = models.DecimalField(max_digits=9, decimal_places=6)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # in km
    estimated_travel_time = models.PositiveIntegerField(null=True, blank=True) # in minutes

    # Pricing snapshot
    pricing_rule_snapshot = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride for {self.rider.username} - {self.status}"
