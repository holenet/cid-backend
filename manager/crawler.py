import requests
from bs4 import BeautifulSoup

from django.db.models import signals
from django.dispatch import receiver
from manager.models import Crawler


@receiver(signals.post_save, sender=Crawler)
def crawl(sender, instance, **kwargs):
    urls = {
        'pop': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN0900',
        'rock': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1000',
        'electronica': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1100',
        'rap/hip-hop': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1200',
        'R&B/soul': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1300',
        'folk/blues/country': 'https://www.melon.com/genre/song_list.htm?gnrCode=GN1400',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0',
    }

    html = requests.get(url=urls['pop'], headers=headers).text
    soup = BeautifulSoup(html, 'html.parser')
    song_list = soup.findChild(name='tbody')
    rows = song_list.findChildren(name='tr')

    for row in rows:
        data = row.findChildren(name='td')

        wrap = data[4].findChildren(name='a')
        title = wrap[0].text
        artist = wrap[1].text

        warp = data[5].findChildren(name='a')
        album = wrap[0].text

        print(f'{album}: {title} - {artist}')
