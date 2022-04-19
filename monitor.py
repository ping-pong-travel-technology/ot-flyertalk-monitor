import json
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseSettings, HttpUrl
from tortoise import fields
from tortoise.models import Model


class Settings(BaseSettings):
    WEBHOOK_URL: Optional[HttpUrl] = None
    POST_TO_SLACK: bool = False


class Thread(Model):
    id = fields.IntField(pk=True)
    title = fields.TextField()
    url = fields.TextField()
    started = fields.DateField()
    seen = fields.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


def main():
    settings = Settings()

    URL_PREFIX = "https://www.flyertalk.com/forum/"
    THREADS_URL = f"{URL_PREFIX}search.php?do=finduser&u=24793&starteronly=1"

    response = requests.get(str(THREADS_URL))
    html = response.content
    soup = BeautifulSoup(html, "html.parser")

    threadslist = soup.find(id="threadslist")
    threads = threadslist.find_all(class_="trow text-center")

    def title_link(tag):
        return tag.has_attr("id") and tag["id"].startswith("thread_title_")

    thread_data = [
        {
            "id": thread.find(title_link)["id"].rsplit("_", 1)[1],
            "title": thread.find(title_link).string,
            "url": URL_PREFIX + thread.find(title_link)["href"],
            "started": thread.find_all("div")[4].find_all("span")[-1].string,
        }
        for thread in threads
    ]
    for thread in thread_data:
        thread_id = thread["id"]
        thread_title = thread["title"]
        thread_url = thread["url"]

        full_url = f"{URL_PREFIX}{thread_url}"
        message = f"David posted to FlyerTalk: {thread_title} - {full_url}"
        if settings.POST_TO_SLACK is True:
            requests.post(
                str(settings.WEBHOOK_URL),
                json.dumps({"text": message}),
                headers={"content-type": "application/json"},
            )


if __name__ == "__main__":
    main()
