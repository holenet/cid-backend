import random
import datetime
from scipy import spatial
import math
import copy
import itertools
import collections

DEBUG = True
"""
  assumptions for debug:
    1. There are 8 genres.
    2. There are 500 artists.
    3. Each music is made by at most three artists.
    4. Each user likes at most three genre.
    5. Each user likes at most 100 artists.
"""


class Muser:
    def __init__(self, pk, gender, birthdate):
        self.id = pk
        self.gender = gender
        self.birthdate = birthdate

        # below two attrs are user's taste
        self.genre = []
        self.artists = []

        num_genre = random.randint(0, 3)
        for _ in range(num_genre):
            g = random.randint(1, 8)
            if g not in self.genre:
                self.genre.append(g)

        num_artists = random.randint(0, 100)
        for _ in range(num_artists):
            a = random.randint(1, 500)
            if a not in self.artists:
                self.artists.append(a)


class Music:
    def __init__(self, pk, title, album, genre, artists, release, length, rating):
        self.id = pk
        self.title = title
        self.album = album
        self.genre = genre
        self.artists = artists
        self.release = release
        self.length = length
        self.rating = rating


class Evaluation:
    def __init__(self, user, music, rating):
        self.user = user
        self.music = music
        self.rating = rating


def construct_random_insts(num_muser, num_music, num_eval):
    users = []
    music = []
    evals = []
    for i in range(num_muser):
        new_user = Muser(pk=i, gender=random.randint(1, 3), birthdate=datetime.datetime.now())
        users.append(new_user)

    for i in range(num_music):
        genre = random.randint(1, 8)  # assume 8 genre

        artists = []
        num_artists = random.randint(1, 5)
        for j in range(num_artists):
            artist = random.randint(1, 500)  # assume 500 artists
            artists.append(artist)

        new_music = Music(pk=i,
                          title="music" + str(i),
                          album="album" + str(i),
                          genre=genre,
                          artists=artists,
                          release=datetime.datetime.now(),
                          length=random.randint(0, 10),
                          rating=random.randint(0, 5))

        music.append(new_music)

    for i in range(num_eval):
        uid = random.randint(0, num_muser - 1)
        mid = random.randint(0, num_music - 1)

        u = users[uid]
        m = music[mid]
        rating = 0

        if m.genre in u.genre:
            rating += 3

        for a in m.artists:
            if a in u.artists:
                rating += 1

        if 5 < rating:
            rating = 5

        if rating != 0:
            new_eval = Evaluation(user=u, music=m, rating=rating)
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

    # print(f'depth: {depth}')
    # for cluster in clusters:
    #     print([p.user_id for p in cluster.elts])

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
                dists.append(9.9)
            else:
                dist = cos_distance(cluster.pos, c.pos, dim)
                dists.append(dist)

        neighbor = cluster
        min_dist = 9.9
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
    num_users = 100
    num_music = 10000
    num_evals = 5000

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
        print(f'cluster {k}: {v}')


if __name__ == '__main__':
    run_clustering()
