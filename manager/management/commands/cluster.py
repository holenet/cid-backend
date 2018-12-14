import collections
import copy
import itertools
import math
import random
import re
import time
from typing import List, Dict

from django.db import transaction
from scipy import spatial

from django.core.management.base import BaseCommand
from chatbot.models import *

DEBUG = True
"""
assumptions for debug:
1. There are 8 genres.
2. There are 500 artists.
3. Each music is made by at most three artists.
4. Each user likes at most three genre.
5. Each user likes at most 100 artists.
"""


class Timer:
    def __init__(self):
        self.stack = []
        self.started = False

    def init(self):
        self.stack = []
        self.started = False

    def indent(self):
        return '  ' * len(self.stack)

    def start(self, message: str):
        if self.started:
            print(f'\n{self.indent()}{message}: ', end='', flush=True)
        else:
            print(f'{self.indent()}{message}: ', end='', flush=True)
        self.stack.append((message, time.time()))
        self.started = True

    def end(self):
        message, start = self.stack.pop()
        end = time.time()
        if self.started:
            print(f'Finished {end - start:.3f} s')
        else:
            print(f'{self.indent()}{message}: Finished {end - start:.3f} s')
        self.started = False

    def info(self, message):
        if self.started:
            print(f'\n{self.indent()}{message}')
        else:
            print(f'{self.indent()}{message}')
        self.started = False


timer = Timer()

genres = set()
artist_pks = set()


class DbgMuser:
    def __init__(self, pk: int, uid: int):
        self.id = pk
        self.uid = uid

        # below two attrs are user's taste
        num_genres = random.randint(0, 3)
        self.genres = random.sample(genres, k=num_genres)

        num_artists = random.randint(0, 100)
        self.artists = random.sample(artist_pks, k=num_artists)


class DbgMusic:
    def __init__(self, pk: int, mid: int, genre: str, artists: List[int]):
        self.id = pk
        self.mid = mid
        self.genre = genre
        self.artists = artists


class DbgEvaluation:
    def __init__(self, user: DbgMuser, music: DbgMusic, rating: int):
        self.user = user
        self.music = music
        self.rating = rating


def construct_random_insts(num_muser: int, num_music: int, num_eval: int):
    users = []
    music = []
    evals = []

    timer.start('Construct Random Musers')
    Muser.objects.filter(username__startswith='dummy').delete()
    with transaction.atomic():
        for i in range(num_muser):
            m = Muser.objects.create(username=f'dummy{i}', password='!Q@W#E$R')
            new_user = DbgMuser(pk=i, uid=m.id)
            users.append(new_user)
    timer.end()

    timer.start('Fetch Real Musers')
    for uid in Muser.objects.exclude(username__startswith='dummy').values_list('id', flat=True):
        new_user = DbgMuser(pk=num_muser, uid=uid)
        users.append(new_user)
        num_muser += 1
    timer.end()

    timer.start('Fetch Musics')
    pk = 0
    for m in Music.objects.prefetch_related('artists').all().iterator():
        new_music = DbgMusic(pk=pk,
                             mid=m.id,
                             genre=m.genre,
                             artists=[aid for aid in m.artists.values_list('id', flat=True)]
                             )
        music.append(new_music)
        pk += 1
        if pk > num_music:  # for debug
            break
    timer.end()

    timer.start('Construct Random Evaluations')
    for u in users:
        bias = random.randint(-2, 2)
        evaluations = []
        for _ in range(num_eval + bias):
            mid = random.randint(0, num_music - 1)
            m = music[mid]
            rating = 0

            if any(g in m.genre for g in u.genres):
                rating += 5
            else:
                rating += random.randint(0, 3)

            for a in m.artists:
                if a in u.artists:
                    rating += 2

            if 10 < rating:
                rating = 10

            evaluations.append(Evaluation(user_id=u.uid,
                                          music_id=m.mid,
                                          rating=rating
                                          )
                               )

            new_eval = DbgEvaluation(user=u, music=m, rating=rating)
            evals.append(new_eval)
        Evaluation.objects.bulk_create(evaluations)
    timer.end()

    return users, music, evals


class Point:
    def __init__(self, user_id: int, pos: Dict[int, float]):
        self.user_id = user_id
        self.pos = pos

    def move(self, a: float, pos: Dict[int, float]):
        merged = collections.defaultdict(list)
        for k, v in itertools.chain(self.pos.items(), pos.items()):
            merged[k].append(v)

        new_pos = {}
        for k, v in merged.items():
            if len(v) == 2:
                new_pos[k] = (1 - a) * v[0] + a * v[1]
            else:
                new_pos[k] = (1 - a) * v[0]

        self.pos = new_pos


class Cluster:
    def __init__(self, elts: List[Point], pos: Dict[int, float]):
        self.elts = elts
        self.pos = pos


def merge(c1: Cluster, c2: Cluster):
    """
    given two clusters, merge them
    """

    p1 = c1.pos
    p2 = c2.pos

    pos = {}
    for axis in p1.keys():
        pos[axis] = p1[axis] / 2

    for axis in p2.keys():
        if axis in p1.keys():
            pos[axis] += p2[axis] / 2
        else:
            pos[axis] = p2[axis] / 2

    return Cluster(c1.elts + c2.elts, pos)


def cos_distance(p1: Dict[int, float], p2: Dict[int, float], dim: int):
    """
    given two points (and dimension), return cosine distance between them.
    """
    axes = []
    for axis in p1:
        if axis in p2:
            axes.append(axis)

    if len(axes) == 0:
        return 1.0

    # choose music about which both users had made evaluations
    vec1 = []
    vec2 = []
    for axis in axes:
        vec1.append(p1[axis])
        vec2.append(p2[axis])

    if all(elt == 0 for elt in vec1) or all(elt == 0 for elt in vec2):
        return 1.0

    return spatial.distance.cosine(vec1, vec2)


def sample(listt: List, num: int):
    """
    Naive sampling implementation O(N + K log(K))
    """
    indices = random.sample(range(len(listt)), num)
    return [listt[i] for i in sorted(indices)]


def h_cluster(clusters: List[Cluster], dim: int, depth: int):
    """
    Hierarchical clustering implementation
    """

    timer.info(f'depth: {depth} ({len(clusters)} clusters) {[len(c.elts) for c in clusters]}')

    if depth == 0:
        return clusters

    merged_clusters = []
    new_clusters = []
    for cluster in clusters:
        # print(f' > {[e.user_id for e in cluster.elts]}')
        if cluster in merged_clusters:
            # print('already merged')
            continue
        dists = {}
        for c in clusters:
            if (c is cluster) or (c in merged_clusters):
                continue
            else:
                dists[c] = cos_distance(cluster.pos, c.pos, dim)

        neighbor = cluster
        min_dist = 9
        for c in clusters:
            if (c is cluster) or (c in merged_clusters):
                continue
            elif dists[c] < min_dist and c not in merged_clusters:
                neighbor = c
                min_dist = dists[c]

        if neighbor is cluster:
            pass
        else:
            # print(f'merge({[e.user_id for e in cluster.elts]}, {[e.user_id for e in neighbor.elts]})')
            new_cluster = merge(cluster, neighbor)
            merged_clusters.append(cluster)
            merged_clusters.append(neighbor)
            new_clusters.append(new_cluster)

    return h_cluster(new_clusters, dim, depth - 1)


def get_representatives(cluster: Cluster, dim: int):
    elts = cluster.elts
    num_elt = len(elts)
    num_rep = int(math.ceil(0.1 * num_elt))

    reps = [0]

    dist = [[0.0] * num_elt for _ in range(num_elt)]
    for i in range(num_elt):
        for j in range(num_elt):
            dist[i][j] = cos_distance(elts[i].pos, elts[j].pos, dim)

    for _ in range(num_rep - 1):
        d = []
        for i in range(num_elt):
            if i in reps:
                d.append(0.0)
            else:
                acc = 0.0
                for r in reps:
                    acc += dist[i][r]
                d.append(acc)

        reps.append(d.index(max(d)))

    reps = [elts[r] for r in reps]
    reps = [Point(-1, copy.deepcopy(r.pos)) for r in reps]

    return reps


def run_clustering():
    """
    CURE Clustering implementation
    TODO: parallelize

    1. Randomly select n points.
    2. Hierarchically cluster those chosen points.
    3. For each cluster, select k representative points.
    4. For each cluster, move chosen representative points 20% closer to its centroid.
    5. Assign all points to clusters that contains representative closest to the point.
    """
    num_users = 1000
    num_music = Music.objects.count()
    num_evals = 50  # average number of eval per dummy

    # Construct random users, music and evaluations.
    timer.start('Construct Random Instances')
    users, music, evals = construct_random_insts(num_users, num_music, num_evals)
    timer.end()

    # Let each user be a point.
    timer.start('Init Clusters')
    points = []
    for u in users:
        pos = {}
        for e in evals:
            if e.user is u:
                pos[e.music.id] = e.rating

        if len(pos) > 0:
            new_point = Point(u.id, pos)
            points.append(new_point)

    # At first, each point is a cluster by itself.
    clusters = []
    for p in points:
        new_cluster = Cluster([p], p.pos)
        clusters.append(new_cluster)
    timer.end()

    # Step 1: Randomly select n points.
    timer.start('Step 1')
    sample_size = int(0.1 * len(clusters))
    selected = sample(clusters, sample_size)
    timer.end()

    timer.start('Step 2, 3, 4')
    # Step 2: Hierarchically cluster selected points.
    selected = h_cluster(selected, num_music, 2)

    cluster_id = 0
    whole_reps = {}
    for cluster in selected:
        # Step 3: select representative points for each cluster
        reps = get_representatives(cluster, num_music)

        # Step 4: move each rep 20% towards the centroid
        for r in reps:
            r.move(0.2, cluster.pos)

        for r in reps:
            whole_reps[r] = cluster_id

        cluster_id += 1
    timer.end()

    # Step 5: Assign all points to clusters that contains the closest rep.
    timer.start('Step 5')
    result = {}
    for i in range(cluster_id):
        result[i] = []

    for p in points:
        closest = 0
        min_dist = 99999999999999
        for r in whole_reps:
            dist = cos_distance(p.pos, r.pos, num_music)
            if dist < min_dist:
                closest = whole_reps[r]
                min_dist = dist

        result[closest].append(p.user_id)
    timer.end()

    timer.info(f'Cluster Sizes: {[(k, len(v)) for k, v in result.items()]}')

    timer.start('Save Clusters')
    for k, v in result.items():
        for u in v:
            user_instance = Muser.objects.get(id=users[u].uid)
            user_instance.cluster = k
            user_instance.save()
    timer.end()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        timer.init()

        timer.start('Gather Genres')
        genres.clear()
        for music in Music.objects.all():
            for genre in re.split('[,/]', music.genre):
                genres.add(genre.strip())
        timer.end()

        timer.start('Fetch Artist Ids')
        artist_pks.clear()
        for a in Artist.objects.all():
            artist_pks.add(a.id)
        timer.end()

        timer.start('Cluster')
        run_clustering()
        timer.end()
