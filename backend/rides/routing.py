from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/rides/(?P<ride_id>\d+)/location/$', consumers.RideLocationConsumer.as_asgi()),
]
