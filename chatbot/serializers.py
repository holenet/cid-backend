from rest_framework import serializers
from chatbot.models import Hotel


class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = ('id', 'name', 'address', 'contact', 'website')
