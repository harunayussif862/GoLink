from django.urls import path, include
from rest_framework_nested import routers
from .views import FareEstimateView, RideRequestViewSet, DriverAvailabilityView, ReviewViewSet, ReportViewSet

app_name = 'rides'

router = routers.DefaultRouter()
router.register('api/rides', RideRequestViewSet, basename='rides')

rides_router = routers.NestedSimpleRouter(router, r'api/rides', lookup='ride')
rides_router.register(r'reviews', ReviewViewSet, basename='ride-reviews')
rides_router.register(r'reports', ReportViewSet, basename='ride-reports')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(rides_router.urls)),
    path('api/rides/fare-estimate/', FareEstimateView.as_view(), name='fare_estimate'),
    path('api/drivers/availability/', DriverAvailabilityView.as_view(), name='driver_availability'),
]
