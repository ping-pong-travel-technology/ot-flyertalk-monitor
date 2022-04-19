import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pendulum
import requests
from bs4 import BeautifulSoup
from pydantic import BaseSettings, HttpUrl
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
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
    console = Console()

    with Progress(
        "[progress.description]{task.description}", SpinnerColumn(), TimeElapsedColumn()
    ) as progress:
        fetch_task = progress.add_task(
            "Fetching threads from https://www.flyertalk.com/", total=1
        )
        URL_PREFIX = "https://www.flyertalk.com/forum/"
        THREADS_URL = f"{URL_PREFIX}search.php?do=finduser&u=24793&starteronly=1"

        response = requests.get(str(THREADS_URL))
        progress.update(fetch_task, completed=1)

        parse_task = progress.add_task("Parsing HTML data for threads", total=1)
        html = response.content
        soup = BeautifulSoup(html, "html.parser")

        threadslist = soup.find(id="threadslist")
        threads = threadslist.find_all(class_="trow text-center")
        progress.update(parse_task, completed=1)

        def title_link(tag):
            return tag.has_attr("id") and tag["id"].startswith("thread_title_")

        process_task = progress.add_task(
            f"Processing {len(threads)} threads", total=len(threads)
        )
        thread_data = []
        for thread in threads:
            thread_data.append(
                {
                    "id": thread.find(title_link)["id"].rsplit("_", 1)[1],
                    "title": thread.find(title_link).string,
                    "url": URL_PREFIX + thread.find(title_link)["href"],
                    "started": thread.find_all("div")[4].find_all("span")[-1].string,
                    "seen": pendulum.now(),
                }
            )
            progress.update(process_task, advance=1)

        new = set()
        with Session(engine) as session:
            check_task = progress.add_task(
                "Checking database for existing threads", total=len(threads)
            )
            for thread in thread_data:
                thread_id = thread["id"]
                statement = select(Thread).where(Thread.id == thread_id)
                result = session.exec(statement)

                if result.first() is None:
                    session.add(Thread(**thread))
                    new.add(thread_id)

                progress.update(check_task, advance=1)

            session.commit()

        if settings.POST_TO_SLACK is True and len(new) > 0:
            notification_task = progress.add_task(
                f"Sending notifications for {len(new)} thread(s)", total=len(new)
            )
            with Session(engine) as session:
                for thread_id in new:
                    statement = select(Thread).where(Thread.id == thread_id)
                    result = session.exec(statement)
                    thread = result.one()

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
                progress.update(notification_task, advance=1)


if __name__ == "__main__":
    if Path(sqlite_file_name).exists() is False:
        create_db_and_tables()

    main()
