import os
import redis
import requests

from bs4 import BeautifulSoup

REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL is not None:
    r = redis.from_url(REDIS_URL)
else:
    r = redis.StrictRedis()

URL_PREFIX = 'https://www.flyertalk.com/forum/'
THREADS_URL = f'{URL_PREFIX}search.php?do=finduser&u=24793&starteronly=1'

response = requests.get(THREADS_URL)
html = response.content
soup = BeautifulSoup(html, 'html.parser')

threadslist = soup.find(id='threadslist')
threads = threadslist.find_all(class_='trow text-center')


def title_link(tag):
    return tag.has_attr('id') and tag['id'].startswith('thread_title_')


thread_data = [
    {
        'id': thread.find(title_link)['id'].rsplit('_', 1)[1],
        'title': thread.find(title_link).string,
        'url': thread.find(title_link)['href'],
        'started': thread.find_all('div')[4].find_all('span')[-1].string,
    } for thread in threads
]
for thread in thread_data:
    thread_id = thread['id']

    if r.exists(thread_id):
        continue

    thread_url = thread['url']
    r.set(thread_id, thread_url)
    print(f'Added {thread_id} - {URL_PREFIX}{thread_url}')
