import re
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
        # Choose one music by original rating
        ratings = list(map(lambda x: x.original_rating, default_candidates))

        idx = 0
        for c in default_candidates:
            for a in c.artists:
                if a in user.fan_artists.all():
                    ratings[idx] += 0.1

            for g in re.split('[,/]', c.genre):
                if g.strip() in user.fan_genres:
                    ratings[idx] += 0.1

            idx += 1

        total_ratings = sum(ratings)
        weights = list(map(lambda x: x / total_ratings, ratings))
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
