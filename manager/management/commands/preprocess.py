import pickle
import time

from django.conf import settings
from django.core.management import BaseCommand

from chatbot.models import Music, Muser, Evaluation


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        start = time.time()
        music_to_artists = {}
        for m in Music.objects.all():
            music_to_artists[m.id] = set(m.artists.values_list('id', flat=True))
        with open(settings.MUSIC_TO_ARTISTS, 'wb') as f:
            pickle.dump(music_to_artists, f)
        end = time.time()
        print(f'music_to_artists {end - start:.2f} s')

        start = time.time()
        cluster_music_to_average_rating = {}
        for cluster in set(Muser.objects.values_list('cluster', flat=True)):
            if cluster is None:
                continue
            users = set(Muser.objects.filter(cluster=cluster).values_list('id', flat=True))
            music_ratings = {}
            for e in Evaluation.objects.filter(user_id__in=users):
                mid = e.music_id
                if mid not in music_ratings:
                    music_ratings[mid] = [e.rating]
                else:
                    music_ratings[mid].append(e.rating)
            for mid in Music.objects.values_list('id', flat=True):
                if mid not in music_ratings:
                    music_ratings[mid] = 0
                else:
                    music_ratings[mid] = sum(music_ratings[mid]) / len(music_ratings[mid])
            cluster_music_to_average_rating[cluster] = music_ratings
        with open(settings.CLUSTER_MUSIC_TO_AVERAGE_RATING, 'wb') as f:
            pickle.dump(cluster_music_to_average_rating, f)
        end = time.time()
        print(f'cluster_music_to_average_rating {end - start:.2f} s')
