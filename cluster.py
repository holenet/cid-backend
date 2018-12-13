
DEBUG = True
"""
  assumptions for debug:
    1. There are 8 genres.
	2. There are 500 artists.
	3. Each music is made by at most three artists.
    4. Each user likes at most three genre.
	5. Each user likes at most 100 artists.
"""

import random
import datetime
from scipy import spatial
import math
import copy
import itertools
import collections


class Muser:
	def __init__(self, _id, _gender, _birthdate):
		self.id = _id
		self.gender = _gender
		self.birthdate = _birthdate

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
	def __init__(self, _id, _title, _album, _genre, _artists, _release, _length, _rating):
		self.id = _id
		self.title = _title
		self.album = _album
		self.genre = _genre
		self.artists = _artists
		self.release = _release
		self.length = _length
		self.rating = _rating


class Evaluation:
	def __init__(self, _user, _music, _rating):
		self.user = _user
		self.music = _music
		self.rating = _rating


def construct_random_insts(num_muser, num_music, num_eval):
	users = []
	music = []
	evals = []
	for i in range(num_muser):
		new_user = Muser(_id=i, _gender=random.randint(1,3), _birthdate=datetime.datetime.now())
		users.append(new_user)

	for i in range(num_music):
		genre = random.randint(1, 8) # assume 8 genre

		artists = []
		num_artists = random.randint(1, 5)
		for j in range(num_artists):
			artist = random.randint(1, 500) # assume 500 artists
			artists.append(artist)

		new_music = Music(_id=i,
				          _title="music"+str(i),
						  _album="album"+str(i), 
						  _genre=random.randint(1,8),
						  _artists=artists,
						  _release=datetime.datetime.now(),
						  _length=random.randint(0, 10),
						  _rating=random.randint(0, 5))
		
		music.append(new_music)

	for i in range(num_eval):
		uid = random.randint(0, num_muser-1)
		mid = random.randint(0, num_music-1)

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
			new_eval = Evaluation(_user=u, _music=m, _rating=rating)
			evals.append(new_eval)
	
	return users, music, evals

class Point:
	def __init__(self, _user_id, _pos):
		self.user_id = _user_id
		self.pos = _pos
	
	def move(self, a, _pos):
		merged = collections.defaultdict(list)
		for k, v in itertools.chain(self.pos.items(), _pos.items()):
			merged[k].append(v)

		new_pos = {}
		for k, v in merged.items():
			if len(v) == 2:
				new_pos[k] = (1-a)*v[0] + a*v[1]
			else:
				new_pos[k] = (1-a)*v[0]

		self.pos = new_pos


class Cluster:
	def __init__(self, _elts, _pos):
		self.elts = _elts
		self.pos = _pos
"""
  given two clusters, merge them
"""
def merge(c1, c2):
	p1 = c1.pos
	p2 = c2.pos

	pos = {}
	for axis in p1.keys():
		pos[axis] = p1[axis]/2

	for axis in p2.keys():
		if axis in p1.keys():
			pos[axis] += p2[axis]/2
		else:
			pos[axis] = p2[axis]/2
	
	return Cluster(c1.elts + c2.elts, pos)

"""
  given two clusters (and dimension), return cosine distance between them.
"""
def cos_distance(c1, c2, dim):
	p1 = c1.pos
	p2 = c2.pos

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

"""
  Naive sampling implementation O(N + K log(K))
  TODO: delveop faster algorithm
"""
def sample(listt, num):
	indices = random.sample(range(len(listt)), num)
	return [listt[i] for i in sorted(indices)]


"""
  Hierarchical clustering implementation
  TODO: parrallelize
"""
def h_cluster(clusters, dim, depth):
	# print(f'depth: {depth}')
	# for cluster in clusters:
	#	 print([p.user_id for p in cluster.elts])

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
				dist = cos_distance(cluster, c, dim)
				dists.append(dist)

		neighbor = cluster
		min_dist = 9.9
		for i in range(len(dists)):
			if dists[i] < min_dist and clusters[i] not in merged_clusters:
				neighbor = clusters[i]
				min_dist = dists[i]
		if neighbor != cluster:
			#print(f'merge({cluster.elts}, {neighbor.elts})')
			new_cluster = merge(cluster, neighbor)
			merged_clusters.append(cluster)
			merged_clusters.append(neighbor)
			new_clusters.append(new_cluster)
		else:
			merged_clusters.append(cluster)
			new_clusters.append(cluster)

	return h_cluster(new_clusters, dim, depth-1)


def get_representatives(cluster, dim):
	elts = cluster.elts
	num_elt = len(elts)
	num_rep = int(math.ceil(0.5 * num_elt))

	reps = [0]
	
	dist = [[0.0] * num_elt for _ in range(num_elt)]
	for i in range(num_elt):
		for j in range(num_elt):
			dist[i][j] = cos_distance(elts[i], elts[j], dim)
	
			
	for _ in range(num_rep-1):
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



"""
  CURE Clustring implementation
  TODO: parallelize

  1. Randomly select n points.
  2. Hierarchically cluster those chosen points.
  3. For each cluster, select k representative points.
  4. For each cluster, move chosen representative points 20% closer to its centroid.
--
  5. Assign all points to clusters that contains representative closest to the point.
"""
def cluster():
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

	for cluster in selected:
		# Step 3: select representative points for each cluster
		reps = get_representatives(cluster, num_music)
		
		# Step 4: move each rep 20% towards the centroid
		for r in reps:
			r.move(0.2, cluster.pos)

cluster()
