from numpy.random import choice

from chatbot.models import Music


def recommend(user, opt):
    candidates = Music.objects.all()
    if 'genre' in opt:
        candidates = candidates.filter(genre__icontains=opt['genre'])
    if 'artist' in opt:
        candidates = candidates.filter(artists__name__icontains=opt['genre'])
    if not candidates:
        return None
    candidates = list(candidates)
    ratings = list(map(lambda x: x.original_rating, candidates))
    total_ratings = sum(ratings)
    weights = list(map(lambda x: x / total_ratings, ratings))
    music = choice(candidates, p=weights)
    return music
