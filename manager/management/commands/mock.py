from django.core.management import BaseCommand

from chatbot.models import *


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        prefix = 'fan_dummy_'
        artist_ids = (35034, 31906, 31982, 33078)
        artists = tuple(Artist.objects.get(id=artist_id) for artist_id in artist_ids)
        num_fans = 200
        for i in range(num_fans):
            if Muser.objects.filter(username=f'{prefix}{i}').exists():
                Muser.objects.filter(username=f'{prefix}{i}').delete()
            fan = Muser.objects.create(username=f'{prefix}{i}', password='!Q@W#E$R')
            for artist in artists:
                Evaluation.objects.bulk_create([Evaluation(user=fan, music=m, rating=10) for m in Music.objects.filter(artists=artist)])

        if Muser.objects.filter(username='target').exists():
            Muser.objects.filter(username='target').delete()
        target = Muser.objects.create(username='target', password='!Q@W#E$R')
        for artist in artists:
            Evaluation.objects.bulk_create([Evaluation(user=target, music=m, rating=10) for m in Music.objects.filter(artists=artist)])
