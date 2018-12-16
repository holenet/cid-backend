import pickle
import re

from django.conf import settings
from numpy.random import choice

from chatbot.models import *


try:
    with open(settings.MUSIC_TO_ARTISTS, 'rb') as f:
        music_to_artists = pickle.load(f)
    print('music_to_artists loaded')
except Exception as e:
    music_to_artists = None
    print(f'music_to_artists does not exist!! {e}')


def recommend(user, opt):
    # Make candidates by option
    candidates = Music.objects.exclude(pk__in=user.recommended.all())
    if 'genre' in opt:
        candidates = candidates.filter(genre__search=opt['genre'])
    if 'artist' in opt:
        candidates = candidates.filter(artists__name__search=opt['artist'])
    if not candidates:
        profit = False
        candidates = Music.objects.exclude(pk__in=user.recommended.all())
    else:
        profit = True

    candidates = list(candidates)
    default_candidates = candidates[:]

    def default_recommend():
        # Choose one music by original rating
        ratings = list(map(lambda x: x.original_rating, default_candidates))
        import time
        last = time.time()
        fan_artists = set(user.fan_artists.all().values_list('id', flat=True))
        l1 = 0
        l2 = 0
        for i, c in enumerate(default_candidates):
            last1 = time.time()
            if music_to_artists:
                for a_id in music_to_artists[c.id]:
                    if a_id in fan_artists:
                        ratings[i] += 0.1
            else:
                for a_id in c.artists.all().values_list('id', flat=True):
                    if a_id in fan_artists:
                        ratings[i] += 0.1
            l1 += time.time() - last1

            last2 = time.time()
            for g in re.split('[,/]', c.genre):
                if g.strip() in user.fan_genres:
                    ratings[i] += 0.1
            l2 += time.time() - last2

        total_ratings = sum(ratings)
        weights = list(map(lambda x: x / total_ratings, ratings))
        music = choice(candidates, p=weights)
        print(f'{time.time() - last:.2f} {l1:.2f} {l2:.2f}')
        return music

    user_evals = user.evaluations.all()
    if len(user_evals) < 10:
        return profit, default_recommend()

    candidate_score = {}
    for c in candidates:
        candidate_score[c.id] = []

    cluster = user.cluster
    if cluster is None:
        # this means clustering has done before user signed up or made evaluations or etc.
        return profit, default_recommend()

    neighbors = Muser.objects.filter(cluster=cluster)
    for n in neighbors:
        neighbor_evals = n.evaluations.all()
        for e in neighbor_evals:
            if e.music_id in candidate_score:
                candidate_score[e.music_id].append(e.rating)

    for mid in candidate_score:
        if Evaluation.objects.filter(user_id=user.id, music_id=mid).exists():
            candidate_score[mid] = 0
        else:
            candidate_score[mid] = 0 if not candidate_score[mid] else (sum(candidate_score[mid]) / len(candidate_score[mid]))

    music = max(candidates, key=lambda c: candidate_score[c.id])
    if candidate_score[music.id] == 0:
        return profit, default_recommend()

    return profit, music
