from django.urls import path
from .views import FareEstimateView

app_name = 'ride_hailing'

urlpatterns = [
    path('api/rides/estimate/', FareEstimateView.as_view(), name='fare_estimate'),
]
