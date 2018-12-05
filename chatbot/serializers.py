from rest_framework import serializers
from chatbot.models import Muser, Message, Music


class MuserSerializer(serializers.ModelSerializer):
    def validate_gender(self, value):
        if 3 <= value:
            raise serializers.ValidationError("gender value must be one of 0, 1, 2")
        return value

    class Meta:
        model = Muser
        fields = ('id', 'username', 'gender', 'birthdate', 'evaluations', 'push_token')
        read_only_fields = ('username', )


class MusicSerializer(serializers.ModelSerializer):
    album_id = serializers.ReadOnlyField(source='album.id')
    album = serializers.StringRelatedField()
    artists = serializers.StringRelatedField(many=True)

    class Meta:
        model = Music
        fields = ('title', 'album_id', 'album', 'artists', 'length')


class MessageSerializer(serializers.ModelSerializer):
    music = MusicSerializer(read_only=True)
    chips = serializers.SerializerMethodField()

    def get_chips(self, obj):
        if isinstance(obj.chips, str):
            return eval(obj.chips)
        return obj.chips

    class Meta:
        model = Message
        fields = ('id', 'created', 'sender', 'receiver', 'text', 'music', 'chips', )
        ordering = ('created', )
