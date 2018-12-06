from __future__ import absolute_import, unicode_literals

import datetime
import os
import time
import traceback
import urllib.request
import urllib.error
import lxml.html

import requests
from django.conf import settings
from django.core.files import File
from django.db.models import signals
from django.dispatch import receiver
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from backend.celery import app
from chatbot.models import Artist, Album, Music, SoloArtist, GroupArtist
from manager.models import Crawler

driver_path = os.path.join(settings.BASE_DIR, 'chromedriver')


@receiver(signals.post_save, sender=Crawler)
def crawl_help(sender, instance, created, **kwargs):
    if created:
        crawl.delay(instance.id)


@app.task
def crawl(crawler_id):
    while True:
        crawler = Crawler.objects.filter(pk=crawler_id).first()
        time.sleep(0.1)
        if crawler is not None:
            break
    crawler.status = 'Crawling'
    crawler.started = datetime.datetime.now()
    crawler.progress = 0
    crawler.save()

    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x1080')
    options.add_argument('disable-gpu')
    options.add_argument('User-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KTHML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')

    driver = webdriver.Chrome(driver_path, chrome_options=options)
    urls = (
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN0900&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1000&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1100&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1200&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1300&steadyYn=Y',
        'https://www.melon.com/genre/song_list.htm?gnrCode=GN1400&steadyYn=Y',
    )
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0'}
    crawled_music_ids = set()
    crawled_album_ids = set()
    crawled_artist_ids = set()
    fully_crawled_artist_ids = set()

    def update_crawler_detail():
        crawler.detail = f'music {len(crawled_music_ids)}, album {len(crawled_album_ids)}, artist {len(crawled_artist_ids)}'

    def update_crawler_elapsed():
        crawler.elapsed = time.time() - crawler.started.timestamp()

    def get_tree(url):
        html = requests.get(url=url, headers=headers).text
        return lxml.html.document_fromstring(html)

    def close_driver():
        try:
            driver.close()
        except Exception as e:
            print(e)
            pass

    def get_id_selenium(link):
        return int(''.join(filter(lambda x: x.isnumeric(), link.get_property('href'))))

    def get_id_lxml(link):
        return int(''.join(filter(lambda x: x.isnumeric(), link.get('href'))))

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

    def crawl_music(music_id, album, stack, rating, artist_ids):
        crawled_music_ids.add(music_id)
        music = Album.objects.filter(original_id=music_id).first()
        if music:
            return music
        stack.append(('music', music_id))

        music_url = f'https://www.melon.com/song/detail.htm?songId={music_id}'
        tree = get_tree(music_url)
        music_title = tree.xpath("//div[@class='song_name']")[0].text_content().replace('곡명', '').strip()

        # Gather Music Information
        music_info = tree.xpath('/html/body/div[1]/div[3]/div/div/form/div/div/div[2]/div[2]/dl')[0]
        info_keys = ('발매일', '장르')
        info_key = None
        info_fields = [None] * len(info_keys)
        for elt in music_info.xpath('.//*'):
            data = elt.text_content().strip()
            if data in info_keys:
                info_key = data
            elif info_key is not None:
                info_fields[info_keys.index(info_key)] = data
                info_key = None

        # Create Music
        music = Music.objects.create(
            original_id=music_id,
            title=music_title,
            album=album,
            release=to_date(info_fields[0]),
            genre=info_fields[1],
            original_rating=rating,
        )

        # Crawl Artists
        for artist_id in artist_ids:
            artist = crawl_artist(artist_id, stack)
            music.artists.add(artist)

        stack.pop()
        return music

    def crawl_album(album_id, stack):
        crawled_album_ids.add(album_id)
        album = Album.objects.filter(original_id=album_id).first()
        if album:
            return album
        stack.append(('album', album_id))
        print(f'{"-"*len(stack)} Album {album_id}')

        album_url = f'https://www.melon.com/album/detail.htm?albumId={album_id}'
        tree = get_tree(album_url)

        album_title = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[1]')[0].text_content().replace('앨범명', '').strip()
        print(f'{"="*len(stack)} {album_title}')

        # Gather Album Information
        album_info = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[2]/dl')[0]
        info_keys = ('발매일', '장르')
        info_key = None
        info_fields = [None] * len(info_keys)
        for elt in album_info.xpath('.//*'):
            data = elt.text_content().strip()
            if data in info_keys:
                info_key = data
            elif info_key is not None:
                info_fields[info_keys.index(info_key)] = data
                info_key = None

        # Download Album Image
        album_image = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[1]/a/img')[0]
        image_url = album_image.get('src').strip()
        try:
            result = urllib.request.urlretrieve(image_url)
            image_path = result[0]
        except urllib.error.URLError:
            image_path = None

        # Create Album
        album = Album.objects.create(
            original_id=album_id,
            title=album_title,
            release=to_date(info_fields[0]),
            genre=info_fields[1],
        )
        if image_path:
            album.image.save(os.path.basename(image_url), File(open(image_path, 'rb')))

        # Gather Artist Ids
        artists = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[3]/div/ul/li[*]/a')
        if not artists:
            artists = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[2]/a[*]')
        artist_ids = set()
        for artist in artists:
            artist_ids.add(get_id_lxml(artist))
        for artist_id in artist_ids:
            artist = crawl_artist(artist_id, stack)
            album.artists.add(artist)

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
            for artist in music_elt.xpath(".//a[contains(@href,'goArtistDetail')]"):
                artist_id_set.add(get_id_lxml(artist))
            if not artist_id_set:
                artist = music_elt.xpath(".//div[@class='ellipsis rank02']")[0].text_content()
                if 'Various Artists' not in artist:
                    raise Exception(f"No artists on music {music_id}")
            music_artist_ids[music_id] = artist_id_set
        for music_id in music_ids:
            crawl_music(music_id, album, stack, music_ratings[music_id], music_artist_ids[music_id])

        print(f'{"."*len(stack)} {album.music.count()}')
        stack.pop()
        return album

    def crawl_artist(artist_id, stack):
        crawled_artist_ids.add(artist_id)
        artist = Artist.objects.filter(original_id=artist_id).first()
        if ('artist', artist_id) in stack or artist_id in fully_crawled_artist_ids:
            return artist
        simple = len(stack) > crawler.level
        if artist and simple:
            return artist
        stack.append(('artist', artist_id))
        print(f'{"-"*len(stack)} Artist {artist_id}')

        artist_url = f'https://www.melon.com/artist/album.htm?artistId={artist_id}'
        tree = get_tree(artist_url)

        # First Creation
        if not artist:
            artist_name = tree.xpath("//p[@class='title_atist']")[0].text_content().replace('아티스트명', '').strip()
            print(f'{"="*len(stack)} {artist_name}')

            # Gather Artist Information
            artist_info = tree.xpath("//dl[@class='atist_info clfix']")[0]
            info_keys = ('활동유형', '데뷔', '소속사', '생일')
            info_key = None
            info_fields = [None] * len(info_keys)
            for elt in artist_info.xpath('.//*'):
                data = elt.text_content().strip()
                if data in info_keys:
                    info_key = data
                elif info_key is not None:
                    info_fields[info_keys.index(info_key)] = data
                    info_key = None
            artist_debut = None
            if info_fields[1] is not None:
                artist_debut = info_fields[1].split()[0]

            # Create SoloArtist
            if info_fields[0] is not None and '솔로' in info_fields[0]:
                artist = SoloArtist.objects.create(original_id=artist_id)
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
                artist = GroupArtist.objects.create(original_id=artist_id)
                artist.name = artist_name
                artist.debut = to_date(artist_debut)
                artist.agent = info_fields[2]
                artist.save()

                members = tree.xpath("//div[@class='wrap_atistname']/a[@class='atistname']")
                member_ids = set()
                for member in members:
                    member_ids.add(get_id_lxml(member))
                for member_id in member_ids:
                    member = crawl_artist(member_id, stack)
                    artist.members.add(member)
            # Create Artist
            else:
                artist = Artist.objects.create(original_id=artist_id)
                artist.name = artist_name
                artist.debut = to_date(artist_debut)
                artist.agent = info_fields[2]
                artist.save()

        # Do not Crawl Heavily
        if simple:
            stack.pop()
            return artist

        # Gather Album Ids
        driver.get(artist_url)
        driver.find_element_by_xpath('//*[@id="POPULAR_ALBUM_LIST"]').click()
        for i in range(100):
            try:
                albums = driver.find_elements_by_xpath('/html/body/div/div[3]/div/div/div[4]/div[2]/form/div/ul/li[*]/div/div/dl/dt/a')
                album_ids = set()
                for album in albums:
                    album_ids.add(get_id_selenium(album))
                for album_id in album_ids:
                    crawl_album(album_id, stack)
            except StaleElementReferenceException:
                continue
            break

        fully_crawled_artist_ids.add(stack.pop()[1])
        return artist

    def crawl_genre(url):
        tree = get_tree(url)

        # Gather Artist Ids
        artists = tree.xpath('/html/body/div/div[3]/div/div/div[7]/form/div/table/tbody/tr[*]/td[5]/div/div/div[2]/a')
        artist_ids = set()
        for i, artist in enumerate(artists):
            artist_ids.add(get_id_lxml(artist))

        for i, artist_id in enumerate(artist_ids):
            yield i, len(artist_ids)
            crawl_artist(artist_id, [])

    last = None
    for i, url in enumerate(urls):
        try:
            for j, t in crawl_genre(url):
                if last is None:
                    last = time.time()
                crawler.refresh_from_db()
                # Cancel
                if crawler.cancel:
                    crawler.status = 'Canceled'
                    crawler.remain = None
                    update_crawler_detail()
                    update_crawler_elapsed()
                    crawler.save()
                    close_driver()
                    print('Crawling Canceled')
                    return
                # Update Progress
                progress = i / len(urls) + j / t / len(urls)
                crawler.status = 'Crawling'
                crawler.progress = 100 * progress
                current = time.time()
                if progress != 0:
                    crawler.remain = (current - last) / progress * (1 - progress)
                update_crawler_detail()
                update_crawler_elapsed()
                crawler.save()
        except:
            # Error
            crawler.status = 'Error Occurred'
            crawler.error = traceback.format_exc()
            crawler.remain = None
            update_crawler_detail()
            update_crawler_elapsed()
            crawler.save()
            close_driver()
            print('Crawling Error Occurred')
            return
    # Finish
    crawler.status = 'Finished'
    crawler.progress = 100
    crawler.remain = None
    update_crawler_elapsed()
    update_crawler_detail()
    crawler.save()
    close_driver()
    print('Crawling Finished')
