from decimal import Decimal
from .models import PricingRule

def calculate_fare(distance, estimated_time, vehicle, pricing_rule, stops=0):
    """
    Calculates the fare for a ride based on a flexible pricing rule.
    """
    # Base fare calculation
    fare = (
        pricing_rule.base_fare +
        (Decimal(distance) * pricing_rule.per_km_rate) +
        (Decimal(estimated_time) * pricing_rule.per_minute_rate)
    )

    # Add-ons
    if vehicle.ac_available:
        fare *= pricing_rule.ac_surcharge

    if vehicle.vehicle_tier == 'premium':
        fare *= pricing_rule.premium_tier_multiplier
    elif vehicle.vehicle_tier == 'vip':
        fare *= pricing_rule.vip_tier_multiplier

    # Stop surcharge (e.g., 25% of initial fare per stop)
    # This is a simplified rule. A more complex rule could be stored in the PricingRule model.
    stop_surcharge = (fare * Decimal('0.25')) * stops
    fare += stop_surcharge

    # Mock surge pricing
    # In a real app, this would be based on demand and supply in the area.
    # surge_multiplier = get_surge_multiplier(pickup_lat, pickup_lon)
    # fare *= surge_multiplier

    return round(fare, 2)

def get_active_pricing_rule():
    """
    Returns the active pricing rule.
    """
    return PricingRule.objects.filter(is_active=True).first()
