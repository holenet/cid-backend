import collections
import copy
import datetime
import itertools
import math
import random
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

genres = {}
artist_pk_bound = {}

class DbgMuser:
    def __init__(self, pk, uid):
        self.id = pk
        self.uid = uid

        # below two attrs are user's taste
        self.genre = []
        self.artists = []

        num_genre = random.randint(0, 3)
        for _ in range(num_genre):
            g = random.randint(0, len(genres))
            if g not in self.genre:
                self.genre.append(g)

        num_artists = random.randint(0, 100)
        for _ in range(num_artists):
            a = random.randint(artist_pk_bound['lo'], artist_pk_bound['hi'])
            if a not in self.artists:
                self.artists.append(a)

class DbgMusic:
    def __init__(self, pk, mid, genre, artists):
        self.id = pk
        self.mid = mid
        self.genre = genre
        self.artists = artists


class DbgEvaluation:
    def __init__(self, user, music, rating):
        self.user = user
        self.music = music
        self.rating = rating


def construct_random_insts(num_muser, num_music, num_eval):
    users = []
    music = []
    evals = []

    for i in range(num_muser):
        try:
            m = Muser.objects.get(username=f'dummy{i}')
            m.delete()
        except Exception as e:
            pass
        m = Muser.objects.create(username=f'dummy{i}', password='!Q@W#E$R')
        new_user = DbgMuser(pk=i, uid=m.id)
        users.append(new_user)
    
    pk = 0
    for m in Music.objects.all():
        new_music = DbgMusic(pk=pk,
                             mid = m.id,
                             genre=m.genre,
                             artists=[a.id for a in m.artists.all()])
    
        music.append(new_music)
        pk += 1
        if pk > num_music: break # for debug

    for u in users:
        bias = random.randint(-2, 2)
        for _ in range(num_eval + bias):
            mid = random.randint(0, num_music - 1)
            m = music[mid]
            rating = 0

            if m.genre in u.genre:
                rating += 3

            for a in m.artists:
                if a in u.artists:
                    rating += 1

            if 5 < rating:
                rating = 5

            Evaluation.objects.create(user=Muser.objects.get(id=u.uid),
                                      music=Music.objects.get(id=m.mid),
                                      rating=rating)

            new_eval = DbgEvaluation(user=u, music=m, rating=rating)
            evals.append(new_eval)

    return users, music, evals

class Point:
    def __init__(self, user_id, pos):
        self.user_id = user_id
        self.pos = pos

    def move(self, a, pos):
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
    def __init__(self, elts, pos):
        self.elts = elts
        self.pos = pos


def merge(c1, c2):
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


def cos_distance(p1, p2, dim):
    """
      given two points (and dimension), return cosine distance between them.
    """

    # choose music about which both users had made evaluations
    vec1 = []
    vec2 = []
    for axis in range(dim):
        if axis in p1.keys() and axis in p2.keys():
            vec1.append(p1[axis])
            vec2.append(p2[axis])

    if len(vec1) == 0:
        return 1.0

    return spatial.distance.cosine(vec1, vec2)


def sample(listt, num):
    """
      Naive sampling implementation O(N + K log(K))
      TODO: develop faster algorithm
    """
    indices = random.sample(range(len(listt)), num)
    return [listt[i] for i in sorted(indices)]


def h_cluster(clusters, dim, depth):
    """
      Hierarchical clustering implementation
    """

    print(f'depth: {depth}')
    for cluster in clusters:
        print([p.user_id for p in cluster.elts])

    if depth == 0:
        return clusters

    merged_clusters = []
    new_clusters = []
    for cluster in clusters:
        if cluster in merged_clusters:
            continue
        dists = []
        for c in clusters:
            if c is cluster:
                dists.append(9999999999999999999)
            else:
                dist = cos_distance(cluster.pos, c.pos, dim)
                dists.append(dist)

        neighbor = cluster
        min_dist = 99999999999999999
        for i in range(len(dists)):
            if dists[i] < min_dist and clusters[i] not in merged_clusters:
                neighbor = clusters[i]
                min_dist = dists[i]
        if neighbor != cluster:
            # print(f'merge({cluster.elts}, {neighbor.elts})')
            new_cluster = merge(cluster, neighbor)
            merged_clusters.append(cluster)
            merged_clusters.append(neighbor)
            new_clusters.append(new_cluster)
        else:
            merged_clusters.append(cluster)
            new_clusters.append(cluster)

    return h_cluster(new_clusters, dim, depth - 1)


def get_representatives(cluster, dim):
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
    num_music = 1000 #Music.objects.count()
    num_evals = 50 # average number of eval per dummy

    # Construct random users, music and evaluations.
    users, music, evals = construct_random_insts(num_users, num_music, num_evals)

    # Let each user be a point.
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

    # Step 1: Randomly select n points.
    sample_size = int(0.3 * len(clusters))
    selected = sample(clusters, sample_size)

    # Step 2: Hierarchically cluster selected points.
    selected = h_cluster(selected, num_music, 10)

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

    # Step 5: Assign all points to clusters that contains the closest rep.
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

    for k, v in result.items():
        print(f'cluster {k}: {sorted(v)}')

    for k, v in result.items():
        for u in v:
            user_instance = Muser.objects.get(id=users[u].uid)
            user_instance.cluster = k
            user_instance.save()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        idx = 0
        for music in Music.objects.all():
            for genre in music.genre.split('/'):
                for genre2 in genre.strip().split(','):
                    if genre2 not in genres:
                        genres[genre2] = idx
                        idx += 1

        artist_pks = [a.id for a in Artist.objects.all()]
        artist_pk_bound['lo'] = min(artist_pks)
        artist_pk_bound['hi'] = max(artist_pks)
        
        run_clustering()

