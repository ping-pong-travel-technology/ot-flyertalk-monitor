import json
import os

import redis
import requests
import typer
from bs4 import BeautifulSoup


def main():
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    POST_TO_SLACK = (
        WEBHOOK_URL is not None
        and os.environ.get("POST_TO_SLACK", "false").lower() == "true"
    )
    REDIS_URL = os.environ.get("REDIS_URL")
    if REDIS_URL is not None:
        r = redis.from_url(REDIS_URL)
    else:
        r = redis.StrictRedis()

    URL_PREFIX = "https://www.flyertalk.com/forum/"
    THREADS_URL = f"{URL_PREFIX}search.php?do=finduser&u=24793&starteronly=1"

    response = requests.get(THREADS_URL)
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
            "url": thread.find(title_link)["href"],
            "started": thread.find_all("div")[4].find_all("span")[-1].string,
        }
        for thread in threads
    ]
    for thread in thread_data:
        thread_id = thread["id"]
        thread_title = thread["title"]
        thread_url = thread["url"]

        if r.exists(thread_id):
            continue

        r.set(thread_id, thread_url)

        full_url = f"{URL_PREFIX}{thread_url}"
        message = f"David posted to FlyerTalk: {thread_title} - {full_url}"
        print(message)
        if POST_TO_SLACK is True:
            requests.post(
                WEBHOOK_URL,
                json.dumps({"text": message}),
                headers={"content-type": "application/json"},
            )


if __name__ == "__main__":
    typer.run(main)
