from rest_framework import generics
from chatbot.models import Artist, SoloArtist, GroupArtist
from chatbot.serializers import ArtistSerializer, SoloArtistSerializer, GroupArtistSerializer

from itertools import chain


class ArtistList(generics.ListAPIView):
    def get_queryset(self):
        return chain(SoloArtist.objects.all(), GroupArtist.objects.all())

    serializer_class = ArtistSerializer


class ArtistDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer


class SoloArtistList(generics.ListCreateAPIView):
    queryset = SoloArtist.objects.all()
    serializer_class = SoloArtistSerializer


class SoloArtistDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = SoloArtist.objects.all()
    serializer_class = SoloArtistSerializer


class GroupArtistList(generics.ListCreateAPIView):
    queryset = GroupArtist.objects.all()
    serializer_class = GroupArtistSerializer


class GroupArtistDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = GroupArtist.objects.all()
    serializer_class = GroupArtistSerializer

