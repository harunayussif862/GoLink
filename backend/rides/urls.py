from django.urls import path
from .views import DriverAvailabilityView, RideRequestView

app_name = 'rides'

urlpatterns = [
    path('api/rides/request/', RideRequestView.as_view(), name='ride_request'),
    path('api/drivers/availability/', DriverAvailabilityView.as_view(), name='driver_availability'),
]
