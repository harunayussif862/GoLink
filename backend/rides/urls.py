from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FareEstimateView, RideRequestViewSet, DriverAvailabilityView

app_name = 'rides'

router = DefaultRouter()
router.register('api/rides', RideRequestViewSet, basename='rides')

urlpatterns = [
    path('api/rides/fare-estimate/', FareEstimateView.as_view(), name='fare_estimate'),
    path('api/drivers/availability/', DriverAvailabilityView.as_view(), name='driver_availability'),
    path('', include(router.urls)),
]
