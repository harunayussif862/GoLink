import json
from channels.generic.websocket import AsyncWebsocketConsumer

class RideLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.ride_group_name = f'ride_{self.ride_id}'

        # Join ride group
        await self.channel_layer.group_add(
            self.ride_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave ride group
        await self.channel_layer.group_discard(
            self.ride_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        lat = text_data_json['lat']
        lon = text_data_json['lon']

        # Send message to ride group
        await self.channel_layer.group_send(
            self.ride_group_name,
            {
                'type': 'location_update',
                'lat': lat,
                'lon': lon
            }
        )

    # Receive message from ride group
    async def location_update(self, event):
        lat = event['lat']
        lon = event['lon']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'lat': lat,
            'lon': lon
        }))
