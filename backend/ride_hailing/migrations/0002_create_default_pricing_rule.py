from django.db import migrations

def create_default_pricing_rule(apps, schema_editor):
    PricingRule = apps.get_model('ride_hailing', 'PricingRule')
    PricingRule.objects.create(
        name='Standard',
        base_fare=15.00,
        per_km_rate=5.00,
        per_minute_rate=0.50,
        ac_surcharge=1.20,
        premium_vehicle_multiplier=1.50,
        is_active=True
    )

class Migration(migrations.Migration):

    dependencies = [
        ('ride_hailing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_pricing_rule),
    ]
