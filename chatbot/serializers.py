from rest_framework import serializers
from chatbot.models import Artist, SoloArtist, GroupArtist


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ('id', 'name', 'debut', 'agent')


class SoloArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoloArtist
        fields = ('id', 'name', 'debut', 'agent', 'birthday', 'member_of')


class GroupArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupArtist
        fields = ('id', 'name', 'debut', 'agent', 'members')
