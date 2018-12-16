import pickle

from django.conf import settings
from django.core.management import BaseCommand

from chatbot.models import Music


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        music_to_artists = {}
        for m in Music.objects.all():
            music_to_artists[m.id] = set()
            for a in m.artists.all():
                music_to_artists[m.id].add(a.id)
        with open(settings.MUSIC_TO_ARTISTS, 'wb') as f:
            pickle.dump(music_to_artists, f)
