from decimal import Decimal

def calculate_fare(distance, ac_enabled=False, vehicle_type='standard'):
    """
    Calculates the fare for a ride based on distance and other factors.
    This is a simplified implementation. In a real application, this would
    involve more complex logic, potentially calling external APIs for
    real-time traffic data, surge pricing, etc.
    """
    base_fare = Decimal('15.00')
    per_km_rate = Decimal('5.00')

    fare = base_fare + (Decimal(distance) * per_km_rate)

    if ac_enabled:
        fare *= Decimal('1.2') # 20% extra for AC

    if vehicle_type == 'premium':
        fare *= Decimal('1.5') # 50% extra for premium vehicle

    return round(fare, 2)
