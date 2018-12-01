from __future__ import absolute_import, unicode_literals

import datetime
import os
import time
import traceback
import urllib.request
import lxml.html

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files import File
from django.db.models import signals
from django.dispatch import receiver
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

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
        crawler = Crawler.objects.get(pk=crawler_id)
        time.sleep(0.1)
        if crawler is not None:
            break
    crawler.status = 'Crawling'
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

    def crawl_album(album_id):
        if Album.objects.filter(original_id=album_id).exists():
            return Album.objects.get(original_id=album_id)
        print(f'______ Album {album_id}')

        album_url = f'https://www.melon.com/album/detail.htm?albumId={album_id}'
        tree = get_tree(album_url)

        album_title = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[1]')[0].text_content().replace('앨범명', '').strip()
        print(f'====== {album_title}')

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
        image_url = album_image.get('src').split('/melon/resize')[0]
        result = urllib.request.urlretrieve(image_url)
        image_path = result[0]

        # Create Album
        album = Album.objects.create(
            original_id=album_id,
            title=album_title,
            release=to_date(info_fields[0]),
            genre=info_fields[1],
        )
        album.image.save(os.path.basename(image_url), File(open(image_path, 'rb')))

        # Gather Artist Ids
        try:
            artists = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[3]/div/ul/li[*]/a')
        except NoSuchElementException:
            artists = tree.xpath('/html/body/div[1]/div[3]/div/div/div[2]/div/div[2]/div[1]/div[2]/a[*]')
        artist_ids = set()
        for artist in artists:
            artist_ids.add(get_id_lxml(artist))
        for artist_id in artist_ids:
            crawl_artist(artist_id)
            album.artists.add(Artist.objects.get(original_id=artist_id))

        # Crawl Music
        driver.get(album_url)
        musics = []
        artist_ids = []
        for music_elt in tree.xpath('/html/body/div[1]/div[3]/div/div/div[3]/form/div/table/tbody/tr[*]'):
            try:
                music_title = music_elt.xpath('.//td[4]/div/div/div[1]/span/a')[0].text_content().strip()
            except NoSuchElementException:
                try:
                    music_title = music_elt.xpath('.//td[4]/div/div/div[1]/span/span[2]')[0].text_content().strip()
                except NoSuchElementException:
                    continue
            print(f'......... {music_title}')

            music, _ = Music.objects.get_or_create(title=music_title, album=album)
            musics.append(music)

            # Gather Artist Ids
            artist_id_set = set()
            for artist in tree.xpath('.//td[4]/div/div/div[2]/a[*]'):
                artist_id_set.add(get_id_lxml(artist))
            artist_ids.append(artist_id_set)

        # Crawl Artists
        for i in range(len(musics)):
            music = musics[i]
            for artist_id in artist_ids[i]:
                artist = crawl_artist(artist_id)
                music.artists.add(artist)

        return album

    def crawl_artist(artist_id):
        if Artist.objects.filter(original_id=artist_id).exists():
            return Artist.objects.get(original_id=artist_id)
        print(f'___ Artist {artist_id}')

        artist_url = f'https://www.melon.com/artist/album.htm?artistId={artist_id}'
        tree = get_tree(artist_url)

        artist_name = tree.xpath('/html/body/div/div[3]/div/div/div[1]/div/div[2]/p')[0].text_content().replace('아티스트명', '').strip()
        print(f'=== {artist_name}')

        # Gather Artist Information
        artist_info = tree.xpath('/html/body/div/div[3]/div/div/div[1]/div/div[2]/dl[1]')[0]
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
        # Create GroupArtist
        elif info_fields[0] is not None and '그룹' in info_fields[0]:
            artist = GroupArtist.objects.create(original_id=artist_id)

            members = tree.xpath('/html/body/div/div[3]/div/div/div[1]/div/div[2]/div/a[*]')
            member_ids = set()
            for member in members:
                member_ids.add(get_id_lxml(member))
            for member_id in member_ids:
                member = crawl_artist(member_id)
                artist.members.add(member)
        # Create Artist
        else:
            artist = Artist.objects.create(original_id=artist_id)
        artist.name = artist_name
        artist.debut = to_date(artist_debut)
        artist.agent = info_fields[2]
        artist.save()

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
                    crawl_album(album_id)
            except StaleElementReferenceException:
                continue
            break

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
            crawl_artist(artist_id)

    last = None
    for i, url in enumerate(urls):
        try:
            for j, t in crawl_genre(url):
                if last is None:
                    last = time.time()
                crawler.refresh_from_db()
                # Cancel
                if crawler.destroy:
                    crawler.status = 'Canceled'
                    crawler.save()
                    close_driver()
                    return
                # Update Progress
                progress = i / len(urls) + j / t / len(urls)
                crawler.progress = 100 * progress
                current = time.time()
                if progress != 0:
                    crawler.remain = (current - last) / progress * (1 - progress)
                crawler.save()
        except:
            # Error
            crawler.status = 'Error'
            crawler.error = traceback.format_exc() + f'\n{driver.current_url}'
            crawler.save()
            close_driver()
            return
    # Finish
    crawler.status = 'Finished'
    crawler.progress = None
    crawler.save()
    close_driver()
    print('Crawling Finished')


@app.task
def crawl_beautifulsoup(crawler_id):
    while True:
        crawler = Crawler.objects.get(pk=crawler_id)
        time.sleep(0.1)
        if crawler is not None:
            break
    crawler.status = 'Crawling'
    crawler.progress = 0
    crawler.save()

    urls = {
        'pop': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN0900&steadyYn=Y',
        'rock/metal': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1000&steadyYn=Y',
        'electronica': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1100&steadyYn=Y',
        'rap/hip-hop': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1200&steadyYn=Y',
        'R&B/soul': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1300&steadyYn=Y',
        'folk/blues/country': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1400&steadyYn=Y',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0',
    }

    def crawl_genre(genre):
        print(f'==================== {genre} ====================')

        url = urls[genre]
        html = requests.get(url=url, headers=headers).text
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.findChild(name='tbody')
        rows = table.findChildren(name='tr')

        artist_ids = set()

        for row in rows:
            data = row.findChildren(name='td')
            wrap = data[4].findChildren(name='a')
            artist_id = wrap[1]['href'].split('.')[2].split("'")[1]
            artist_ids.add(artist_id)

        for i, artist_id in enumerate(artist_ids):
            yield i, len(artist_ids)

            artist_url = "https://www.melon.com/artist/song.htm?artistId=" + str(artist_id)
            html = requests.get(url=artist_url, headers=headers).text
            soup = BeautifulSoup(html, 'html.parser')

            artist_name = soup.find(name='p', attrs={'class': 'title_atist'}).text[5:]
            artist, _ = Artist.objects.get_or_create(name=artist_name)

            print(f'> {artist_name}')

            table = soup.findChild(name='tbody')
            rows = table.findChildren(name='tr')
            for row in rows:
                if str(row)[11:13] != 'no':
                    data = row.findChildren(name='td')
                    music_title = data[2].find(name='a', attrs={'class': 'fc_gray'}).string
                    album_title = data[4].find(name='a', attrs={'class': 'fc_mgray'}).string

                    album, _ = Album.objects.get_or_create(title=album_title)
                    album.artists.add(artist)

                    music, _ = Music.objects.get_or_create(title=music_title, album=album, genre=genre)
                    music.artists.add(artist)

    last = None
    for i, genre in enumerate(urls):
        try:
            for j, t in crawl_genre(genre):
                if not last:
                    last = time.time()
                crawler.refresh_from_db()
                if crawler.destroy:
                    crawler.status = 'Canceled'
                    crawler.save()
                    return
                progress = i / len(urls) + j / t / len(urls)
                crawler.progress = 100 * progress
                current = time.time()
                if progress != 0:
                    crawler.remain = (current - last) / progress * (1 - progress)
                print(f'...{crawler.progress} %')
                crawler.save()
        except Exception as e:
            crawler.status = 'Error'
            crawler.error = str(e)
            crawler.save()
            return

    crawler.status = 'Finished'
    crawler.progress = None
    crawler.save()
    print('Crawling finished')
