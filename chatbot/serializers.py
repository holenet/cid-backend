from rest_framework import serializers
from chatbot.models import Muser, Message


class MuserSerializer(serializers.ModelSerializer):
    def validate_gender(self, value):
        if 3 <= value:
            raise serializers.ValidationError("gender value must be one of 0, 1, 2")
        return value

    class Meta:
        model = Muser
        fields = ('id', 'username', 'gender', 'birthdate', 'evaluations', 'push_token')
        read_only_fields = ('username', )


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'created', 'sender', 'receiver', 'text', 'music', 'chips', )
        ordering = ('created', )
