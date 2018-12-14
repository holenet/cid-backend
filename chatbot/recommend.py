from numpy.random import choice

from chatbot.models import *


def recommend(user, opt):
    # Make candidates by option
    candidates = Music.objects.all()
    if 'genre' in opt:
        candidates = candidates.filter(genre__icontains=opt['genre'])
    if 'artist' in opt:
        candidates = candidates.filter(artists__name__icontains=opt['artist'])
    if not candidates:
        profit = False
        candidates = Music.objects.all()
    else:
        profit = True

    candidates = list(candidates)
    default_candidates = candidates[:]
    def default_recommend():
        # Choose one music by original rating
        ratings = list(map(lambda x: x.original_rating, default_candidates))
        total_ratings = sum(ratings)
        weights = list(map(lambda x: x / total_ratings, ratings))
        music = choice(candidates, p=weights)
        return music

    user_evals = user.evaluations.all()
    if len(user_evals) < 10:
        return profit, default_recommend()
    candidate_score = {}
    for c in candidates:
        candidate_score[c] = []

    cluster = user.cluster
    if cluster is None:
        # this means clustring has done before user signed up or made evaluations or etc.
        return profit, default_recommend()
            
    neighbors = Muser.objects.filter(cluster=cluster)
    for n in neighbors:
        neighbor_evals = n.evaluations.all()
        for e in neighbor_evals:
            if e.music in candidates:
                candidate_score[e.music].append(e.rating)

    for c in candidates:
        candidate_score[c] = 0 if not candidate_score[c] else (sum(candidate_score[c]) / len(candidate_score[c]))
    music = max(candidates, key=lambda c: candidate_score[c])
    if candidate_score[music] == 0:
        return profit, default_candidates()
    
    return profit, music

