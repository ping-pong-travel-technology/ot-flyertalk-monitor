import json
from typing import Optional

import pendulum
import requests
from bs4 import BeautifulSoup
from pydantic import BaseSettings, HttpUrl
from sqlitedict import SqliteDict

db = SqliteDict("threads.sqlite", encode=json.dumps, decode=json.loads)


class Settings(BaseSettings):
    WEBHOOK_URL: Optional[HttpUrl] = None
    POST_TO_SLACK: bool = False


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
            "seen": pendulum.now().to_iso8601_string(),
            "notified": False,
        }
        for thread in threads
    ]

    new = set()
    for thread in thread_data:
        thread_id = thread["id"]

        if thread_id not in db:
            db[thread_id] = thread
            new.add(thread_id)

    if len(new) > 0:
        for thread_id in new:
            thread = db[thread_id]
            thread_title = thread["title"]
            thread_url = thread["url"]
            if settings.POST_TO_SLACK is True:
                try:
                    requests.post(
                        str(settings.WEBHOOK_URL),
                        json.dumps(
                            {
                                "text": f"David posted to FlyerTalk: {thread_title} - {thread_url}"
                            }
                        ),
                        headers={"content-type": "application/json"},
                    )
                except Exception:
                    pass
                else:
                    thread["notified"] = True
                    db[thread_id] = thread

    db.commit()


if __name__ == "__main__":
    main()
