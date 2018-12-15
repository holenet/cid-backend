from __future__ import absolute_import, unicode_literals

import datetime
import os
import threading
import time
import traceback
import urllib.request
import urllib.error
from queue import Queue
from random import shuffle

import lxml.html

import requests
from django.conf import settings
from django.core.files import File
from django.db.models import signals
from django.dispatch import receiver
from requests.exceptions import SSLError
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from backend.celery import app
from chatbot.models import Artist, Album, Music, SoloArtist, GroupArtist
from manager.models import Crawler

driver_path = os.path.join(settings.BASE_DIR, 'chromedriver')
headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0'}


@receiver(signals.post_save, sender=Crawler)
def crawl_help(sender, instance, created, **kwargs):
    if created:
        # crawl.delay(instance.id)
        crawl(instance.id)


def get_tree(url):
    html = None
    for i in range(10):
        try:
            html = requests.get(url=url, headers=headers).text
        except SSLError:
            continue
        break
    if html is None:
        html = requests.get(url=url, headers=headers).text
    return lxml.html.document_fromstring(html)


def get_id_selenium(link):
    return int(''.join(filter(lambda x: x.isnumeric(), link.get_property('href'))))


def get_id_lxml(link):
    return int(''.join(filter(lambda x: x.isnumeric(), link.get('href'))))


def get_info(elt_list, info_keys):
    info_key = None
    info_fields = [None] * len(info_keys)
    for elt in elt_list.xpath('.//*'):
        data = elt.text_content().strip()
        if data in info_keys:
            info_key = data
        elif info_key is not None:
            info_fields[info_keys.index(info_key)] = data
            info_key = None
    return info_fields


def to_date(text: None):
    if text is None:
        return None
    text = text.replace('.', '-')
    while text.count('-') < 2:
        text += '-01'
    try:
        datetime.datetime.strptime(text, '%Y-%m-%d')
    except ValueError:
        return None
    return text


def crawl_music(worker_id, music_id, album_id, rating, artist_ids):
    music_url = f'https://www.melon.com/song/detail.htm?songId={music_id}'
    tree = get_tree(music_url)
    music_title = tree.xpath("//div[@class='song_name']")[0].text_content().replace('곡명', '').strip()
    nineteen = tree.xpath("//span[@class='bullet_icons age_19 large']")
    if nineteen:
        music_title = music_title.replace(nineteen[0].text_content(), '').strip()

    # Gather Music Information
    music_info = tree.xpath('/html/body/div[1]/div[3]/div/div/form/div/div/div[2]/div[2]/dl')
    if not music_info:
        music_info = tree.xpath('/html/body/div[1]/div[3]/div/div/form/div/div[1]/div[2]/div/div[2]/dl')[0]
    else:
        music_info = music_info[0]
    info_keys = ('발매일', '장르')
    info_fields = get_info(music_info, info_keys)

    # Create Music
    music, _ = Music.objects.get_or_create(original_id=music_id)
    music.original_id = music_id
    music.title = music_title
    music.release = to_date(info_fields[0])
    music.genre = info_fields[1]
    music.original_rating = rating
    music.save()

    return music_id, album_id, artist_ids


def crawl_album(worker_id, album_id):
    album_url = f'https://www.melon.com/album/detail.htm?albumId={album_id}'
    tree = get_tree(album_url)
    album_title = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[1]')[0].text_content().replace('앨범명', '').strip()
    print(f'{worker_id:02d} Album {album_id} {album_title}')

    # Gather Album Information
    album_info = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[2]/dl')[0]
    info_keys = ('발매일', '장르')
    info_fields = get_info(album_info, info_keys)

    # Download Album Image
    album_image = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[1]/a/img')[0]
    image_url = album_image.get('src').strip()
    try:
        result = urllib.request.urlretrieve(image_url)
        image_path = result[0]
    except urllib.error.URLError:
        image_path = None

    # Create Album
    album, _ = Album.objects.get_or_create(original_id=album_id)
    album.title = album_title
    album.release = to_date(info_fields[0])
    album.genre = info_fields[1]
    if image_path:
        album.image.save(os.path.basename(image_url), File(open(image_path, 'rb')))
    album.save()

    # Gather Artist Ids
    artists = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[3]/div/ul/li[*]/a')
    if not artists:
        artists = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[2]/a[*]')
    artist_ids = set()
    for artist in artists:
        artist_ids.add(get_id_lxml(artist))

    # Gather Music Ids
    music_ids = set()
    music_ratings = dict()
    music_artist_ids = dict()
    for music_elt in tree.xpath('//form/div/table/tbody/tr[*]'):
        music = music_elt.xpath(".//a[contains(@href,'goSongDetail')]")
        if not music:
            continue
        music_id = get_id_lxml(music[0])
        music_ids.add(music_id)

        rating = int(music_elt.xpath(".//button/span[@class='cnt']")[0].text_content().replace('총건수', '').strip())
        music_ratings[music_id] = rating

        artist_id_set = set()
        for artist in music_elt.xpath(".//div[@class='ellipsis rank02']//a[contains(@href,'goArtistDetail')]"):
            artist_id_set.add(get_id_lxml(artist))
        if not artist_id_set:
            artist = music_elt.xpath(".//div[@class='ellipsis rank02']")[0].text_content()
            if 'Various Artists' not in artist:
                raise Exception(f"No artists on music {music_id}")
        music_artist_ids[music_id] = artist_id_set

    return album_id, artist_ids, music_ids, music_ratings, music_artist_ids


def crawl_artist(worker_id, artist_id, driver, simple):
    artist_url = f'https://www.melon.com/artist/song.htm?artistId={artist_id}'
    tree = get_tree(artist_url)

    # First Creation
    artist = Artist.objects.filter(original_id=artist_id).first()
    member_ids = set()
    if artist:
        if not simple:
            print(f'{worker_id:02d} Artist {artist_id} {artist.name}')
    else:
        artist_name = tree.xpath("//p[@class='title_atist']")[0].text_content().replace('아티스트명', '').strip()
        print(f'{worker_id:02d} Artist {artist_id} {artist_name}')

        # Gather Artist Information
        artist_info = tree.xpath("//dl[@class='atist_info clfix']")[0]
        info_keys = ('활동유형', '데뷔', '소속사', '생일')
        info_fields = get_info(artist_info, info_keys)
        artist_debut = None
        if info_fields[1] is not None:
            artist_debut = info_fields[1].split()[0]

        # Create SoloArtist
        if info_fields[0] is not None and '솔로' in info_fields[0]:
            artist, _ = SoloArtist.objects.get_or_create(original_id=artist_id)
            artist_gender = None
            if '남성' in info_fields[0]:
                artist_gender = True
            if '여성' in info_fields[0]:
                artist_gender = False
            artist.gender = artist_gender
            artist.birthday = to_date(info_fields[3])
            artist.name = artist_name
            artist.debut = to_date(artist_debut)
            artist.agent = info_fields[2]
            artist.save()
        # Create GroupArtist
        elif info_fields[0] is not None and '그룹' in info_fields[0]:
            artist, _ = GroupArtist.objects.get_or_create(original_id=artist_id)
            artist.name = artist_name
            artist.debut = to_date(artist_debut)
            artist.agent = info_fields[2]
            artist.save()

            members = tree.xpath("//div[@class='wrap_atistname']/a[@class='atistname']")
            for member in members:
                member_ids.add(get_id_lxml(member))
        # Create Artist
        else:
            artist, _ = Artist.objects.get_or_create(original_id=artist_id)
            artist.name = artist_name
            artist.debut = to_date(artist_debut)
            artist.agent = info_fields[2]
            artist.save()

    # Do not Crawl Heavily
    if simple:
        return artist_id, set(), member_ids

    # Gather Album Ids
    driver.get(artist_url)
    driver.find_element_by_xpath('//*[@id="POPULAR_SONG_LIST"]').click()
    album_ids = set()
    for i in range(100):
        try:
            albums = driver.find_elements_by_xpath('/html/body/div/div[3]/div/div/div[4]/div[2]/form/div/table/tbody/tr[*]/td[5]/div/div/a')
            for album in albums:
                album_ids.add(get_id_selenium(album))
        except StaleElementReferenceException:
            continue
        break

    return artist_id, album_ids, member_ids


@app.task
def crawl(crawler_id):
    while True:
        crawler = Crawler.objects.filter(pk=crawler_id).first()
        if crawler is not None:
            break
        time.sleep(0.1)
    crawler.status = 'Crawling'
    crawler.started = datetime.datetime.now()
    crawler.progress = 0
    crawler.save()

    crawling_thread_num = crawler.thread
    relating_thread_num = crawler.thread
    whole_task = 10 / crawling_thread_num + 1 / relating_thread_num
    crawling_ratio = 10 / crawling_thread_num / whole_task
    relating_ratio = 1 / relating_thread_num / whole_task

    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x1080')
    options.add_argument('disable-gpu')
    options.add_argument('User-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KTHML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')

    urls = (
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN0900&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1000&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1100&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1200&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1300&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1400&steadyYn=Y',
    )

    crawled_ids = {'music': set(), 'album': set(), 'artist': set()}
    relations = {'music': {}, 'album': {}, 'artist': {}}
    fully_crawled_artist_ids = set()
    queue = Queue()
    error = Queue()
    threading_lock = threading.Lock()
    max_depth = crawler.level

    def update_crawler():
        crawler.detail = f'music {len(crawled_ids["music"])}, album {len(crawled_ids["album"])}, artist {len(crawled_ids["artist"])}'
        crawler.elapsed = time.time() - crawler.started.timestamp()
        crawler.save()

    def is_crawled(crawl_type, crawl_id, simple):
        if 'artist' == crawl_type:
            with threading_lock:
                if crawl_id in fully_crawled_artist_ids:
                    return True
                if simple and crawl_id in crawled_ids[crawl_type]:
                        return True
                crawled_ids[crawl_type].add(crawl_id)
                if not simple:
                    fully_crawled_artist_ids.add(crawl_id)
            return False
        with threading_lock:
            if crawl_id in crawled_ids[crawl_type]:
                return True
            crawled_ids[crawl_type].add(crawl_id)
        return False

    def emtpy_kwarg_list(id_list):
        return [(i, {}) for i in id_list]

    def worker(worker_id):
        print(f'Worker {worker_id} Spawned')
        driver = webdriver.Chrome(driver_path, chrome_options=options)

        def close_driver():
            try:
                driver.close()
            except Exception as e:
                print(e)
                pass
        while True:
            crawl_type, crawl_id, depth, kwargs = queue.get()
            if crawl_type is None:
                break
            try:
                # Run Work Items
                to_do_ids = {'music': set(), 'album': set(), 'artist': set()}
                if crawl_type == 'music':
                    music_id, album_id, artist_ids = crawl_music(worker_id, crawl_id, **kwargs)
                    relations['music'][music_id] = (album_id, artist_ids)
                    to_do_ids['album'] = [(album_id, {})]
                    to_do_ids['artist'] = emtpy_kwarg_list(artist_ids)
                elif crawl_type == 'album':
                    album_id, artist_ids, music_ids, music_ratings, music_artist_ids = crawl_album(worker_id, crawl_id)
                    if artist_ids:
                        relations['album'][album_id] = artist_ids
                    to_do_ids['artist'] = emtpy_kwarg_list(artist_ids)
                    to_do_ids['music'] = [(music_id, {'album_id': album_id, 'rating': music_ratings[music_id], 'artist_ids': music_artist_ids[music_id]}) for music_id in music_ids]
                elif crawl_type == 'artist':
                    artist_id, album_ids, member_ids = crawl_artist(worker_id, crawl_id, driver, depth > max_depth)
                    if member_ids:
                        relations['artist'][artist_id] = member_ids
                    to_do_ids['album'] = emtpy_kwarg_list(album_ids)
                    to_do_ids['artist'] = emtpy_kwarg_list(member_ids)
                else:
                    raise Exception(f"Illegal argument crawl_type: {crawl_type}")

                # Add Work Items
                for crawl_type in ('music', 'album', 'artist'):
                    for crawl_id, kwargs in to_do_ids[crawl_type]:
                        if not is_crawled(crawl_type, crawl_id, depth + 1 > max_depth):
                            queue.put((crawl_type, crawl_id, depth + 1, kwargs))
            except:
                # Alert to Main Thread That An Exception Has Occurred
                error.put(f'{traceback.format_exc()}\n{(crawl_type, crawl_id, depth, kwargs)} on Worker {worker_id}')
                break
            finally:
                queue.task_done()
        close_driver()
        print(f'Worker {worker_id} Buried...')

    # Spawn Worker Threads
    workers = []
    for i in range(crawling_thread_num):
        t = threading.Thread(target=worker, args=(i + 1,))
        workers.append(t)
        t.daemon = True
        t.start()

    def join():
        with queue.mutex:
            queue.queue.clear()
        for _ in range(len(workers)):
            queue.put((None, None, None, None))
        for th in workers:
            th.join()

    # Gather Initial Artist Ids
    artist_ids = set()
    for url in urls:
        tree = get_tree(url)

        artists = tree.xpath('/html/body/div/div[3]/div/div/div[7]/form/div/table/tbody/tr[*]/td[5]/div/div/div[2]/a')
        for artist in artists:
            artist_ids.add(get_id_lxml(artist))

    # Put Initial Work Items
    last_time = time.time()
    for i, artist_id in enumerate(artist_ids):
        crawler.refresh_from_db()
        # Cancel
        if crawler.cancel:
            crawler.status = 'Canceled'
            crawler.remain = None
            update_crawler()
            join()
            print('Crawling Canceled')
            return

        # Update Progress
        progress = crawling_ratio * i / len(artist_ids)
        crawler.status = 'Crawling'
        crawler.progress = 100 * progress
        current_time = time.time()
        if progress != 0:
            crawler.remain = (current_time - last_time) / progress * (1 - progress)
        update_crawler()

        # Put Work Item
        if not is_crawled('artist', artist_id, False):
            queue.put(('artist', artist_id, 0, {}))

            # Wait While Observing Errors
            while queue.unfinished_tasks:
                if error.unfinished_tasks:
                    crawler.status = 'Error Occurred'
                    error_message = error.get()
                    print(error_message)
                    crawler.error = error_message
                    crawler.remain = None
                    update_crawler()
                    join()
                    print('Crawling Error Occurred')
                    return
                time.sleep(1)

    # Crawling Finish
    crawler.status = 'Relation Constructing'
    crawler.progress = 50
    crawler.remain = None
    update_crawler()
    join()
    print('Crawling Finished')

    queue = Queue()
    error = Queue()

    def worker(worker_id):
        print(f'Worker {worker_id} Spawned')

        while True:
            chunk = queue.get()
            if chunk is None:
                break
            print(f'{chunk[0][0]} {chunk[0][1]}...{len(chunk)}')
            for model_type, model_id, arg1, arg2 in chunk:
                try:
                    if model_type == 'music':
                        music = Music.objects.get(original_id=model_id)
                        music.album = Album.objects.get(original_id=arg1)
                        for artist_id in arg2:
                            music.artists.add(Artist.objects.get(original_id=artist_id))
                        music.save()
                    elif model_type == 'album':
                        album = Album.objects.get(original_id=model_id)
                        for artist_id in arg1:
                            album.artists.add(Artist.objects.get(original_id=artist_id))
                        album.save()
                    elif model_type == 'artist':
                        artist = GroupArtist.objects.get(original_id=model_id)
                        for member_id in arg1:
                            artist.members.add(Artist.objects.get(original_id=member_id))
                        artist.save()
                    else:
                        raise Exception(f"Illegal argument model_type: {model_type}")
                    time.sleep(0.05)
                except:
                    # Alert to Main Thread That An Exception Has Occurred
                    error.put(f'{traceback.format_exc()}\n{(model_type, model_id, arg1, arg2)} on Worker {worker_id}')
                    break
            queue.task_done()
        print(f'Worker {worker_id} Buried...')

    # Spawn Worker Threads
    workers = []
    for i in range(relating_thread_num):
        t = threading.Thread(target=worker, args=(i + 1,))
        workers.append(t)
        t.daemon = True
        t.start()

    def join():
        with queue.mutex:
            queue.queue.clear()
        for _ in range(len(workers)):
            queue.put(None)
        for th in workers:
            th.join()

    # Make Work Items
    chunk_size = 10
    items = []
    music_list = list(relations['music'].items())
    for i in range(0, len(music_list), chunk_size):
        music_chunk = music_list[i:i+chunk_size]
        items.append([('music', music_id, album_id, artist_ids) for music_id, (album_id, artist_ids) in music_chunk])
    album_list = list(relations['album'].items())
    for i in range(0, len(album_list), chunk_size):
        album_chunk = album_list[i:i+chunk_size]
        items.append([('album', album_id, artist_ids, None) for album_id, artist_ids in album_chunk])
    artist_list = list(relations['artist'].items())
    for i in range(0, len(artist_list), chunk_size):
        artist_chunk = artist_list[i:i+chunk_size]
        items.append([('artist', artist_id, member_ids, None) for artist_id, member_ids in artist_chunk])
    shuffle(items)

    def provider():
        for chunk in items:
            queue.put(chunk)

    # Put and Wait
    t = threading.Thread(target=provider)
    t.daemon = True
    t.start()
    total = len(items)
    last_time = time.time()
    while queue.unfinished_tasks:
        crawler.refresh_from_db()
        # Cancel
        if crawler.cancel:
            crawler.status = 'Canceled'
            crawler.remain = None
            update_crawler()
            join()
            print('Crawling Canceled')
            return

        # Update Progress
        progress = crawling_ratio + relating_ratio * (total - queue.unfinished_tasks) / total
        crawler.status = 'Relating'
        crawler.progress = 100 * progress
        current_time = time.time()
        if progress - crawling_ratio != 0:
            crawler.remain = (current_time - last_time) / (progress - crawling_ratio) * (1 - progress)
        update_crawler()

        for _ in range(10):
            if not queue.unfinished_tasks:
                break
            if error.unfinished_tasks:
                crawler.status = 'Error Occurred'
                error_message = error.get()
                print(error_message)
                crawler.error = error_message
                crawler.remain = None
                update_crawler()
                join()
                print('Relating Error Occurred')
                return
            time.sleep(1)

    # Relating Finish
    crawler.status = 'Finished'
    crawler.progress = 100
    crawler.remain = None
    update_crawler()
    join()
    print('Entire Crawling Finished')
