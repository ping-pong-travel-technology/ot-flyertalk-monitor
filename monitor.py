import maya
import requests

from bs4 import BeautifulSoup

THREADS_URL = 'https://www.flyertalk.com/forum/search.php?do=finduser&u=24793&starteronly=1'  # noqa

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
    started = maya.parse(
        thread['started'].split(' ', 1)[1]
    ).datetime().isoformat()
    title = thread['title']
    id = thread['id']
    print(f'{started} - {id} - {title}')
