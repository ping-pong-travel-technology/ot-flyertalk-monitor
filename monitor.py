import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pendulum
import requests
from bs4 import BeautifulSoup
from pydantic import BaseSettings, HttpUrl
from sqlmodel import Field, Session, SQLModel, create_engine, select


class Thread(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str
    url: str
    started: str
    seen: Optional[datetime]
    notified: Optional[bool] = False


sqlite_file_name = "threads.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


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
            "seen": pendulum.now(),
        }
        for thread in threads
    ]

    new = set()
    with Session(engine) as session:
        for thread in thread_data:
            thread_id = thread["id"]
            statement = select(Thread).where(Thread.id == thread_id)
            result = session.exec(statement)

            if result.first() is None:
                session.add(Thread(**thread))
                new.add(thread_id)

        session.commit()

    if len(new) > 0:
        with Session(engine) as session:
            for thread_id in new:
                statement = select(Thread).where(Thread.id == thread_id)
                result = session.exec(statement)
                thread = result.one()

                if settings.POST_TO_SLACK is True:
                    try:
                        requests.post(
                            str(settings.WEBHOOK_URL),
                            json.dumps(
                                {
                                    "text": f"David posted to FlyerTalk: {thread.title} - {thread.url}"
                                }
                            ),
                            headers={"content-type": "application/json"},
                        )
                    except Exception:
                        pass
                    else:
                        thread.notified = True
                        session.add(thread)
                        session.commit()


if __name__ == "__main__":
    if Path(sqlite_file_name).exists() is False:
        create_db_and_tables()

    main()
