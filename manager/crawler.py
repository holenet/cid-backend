import requests
from bs4 import BeautifulSoup

from django.db.models import signals
from django.dispatch import receiver
from manager.models import Crawler
from chatbot.models import Artist, Music, Album


def crawl_genre(genre, url, headers):
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

    for artist_id in artist_ids:
        artist_url = "https://www.melon.com/artist/song.htm?artistId=" + str(artist_id)
        html = requests.get(url=artist_url, headers=headers).text
        soup = BeautifulSoup(html, 'html.parser')

        artist_name = soup.find(name='p', attrs={'class': 'title_atist'}).text[5:]
        artist, _ = Artist.objects.get_or_create(name=artist_name)

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


@receiver(signals.post_save, sender=Crawler)
def crawl(sender, instance, **kwargs):
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

    for genre, url in urls.items():
        crawl_genre(genre, url, headers)
        # Thread(target=crawl_genre, args=(genre, url, headers, )).start()
