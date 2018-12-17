import pickle
import re

from django.conf import settings
from numpy.random import choice

from chatbot.models import *


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
        print('default')
        # Choose one music by original rating
        ratings = [x.original_rating for x in default_candidates]
        total_original_rating = sum(ratings)
        ratings = [10 * r / total_original_rating for r in ratings]
        fan_artists = set(user.fan_artists.all().values_list('id', flat=True))
        artist_point = 1
        genre_point = 1
        try:
            with open(settings.MUSIC_TO_ARTISTS, 'rb') as f:
                music_to_artists = pickle.load(f)
            print('mu su')
        except Exception as e:
            music_to_artists = None
            print('music_to_artists ERROR')
        for i, c in enumerate(default_candidates):
            if music_to_artists:
                artist_id_set = music_to_artists[c.id]
            else:
                artist_id_set = c.artists.all().values_list('id', flat=True)

            for a_id in artist_id_set:
                if a_id in fan_artists:
                    ratings[i] += artist_point

            for g in re.split('[,/]', c.genre):
                if g.strip() in user.fan_genres:
                    ratings[i] += genre_point

        ratings = [r ** 2 for r in ratings]
        total_ratings = sum(ratings)
        weights = [r / total_ratings for r in ratings]
        music = choice(candidates, p=weights)
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

    try:
        with open(settings.CLUSTER_MUSIC_TO_AVERAGE_RATING, 'rb') as f:
            cluster_music_to_average_rating = pickle.load(f)
    except Exception as e:
        cluster_music_to_average_rating = None
        print('cluster.... Error')

    if cluster_music_to_average_rating:
        for mid in candidate_score:
            candidate_score[mid] = cluster_music_to_average_rating[cluster][mid]
    else:
        neighbors = Muser.objects.filter(cluster=cluster)
        for n in neighbors:
            neighbor_evals = n.evaluations.all()
            for e in neighbor_evals:
                if e.music_id in candidate_score:
                    candidate_score[e.music_id].append(e.rating)

        for mid in candidate_score:
            candidate_score[mid] = 0 if not candidate_score[mid] else (sum(candidate_score[mid]) / len(candidate_score[mid]))

    music = max(candidates, key=lambda c: candidate_score[c.id])
    if candidate_score[music.id] == 0:
        return profit, default_recommend()

    return profit, music
