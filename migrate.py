import redis
from rich import print
from sqlmodel import Session, select

from monitor import Thread, engine

REDIS_URL = "redis://:pf6020c76fa33ec61712240f0fd8c96793618cef9707b927fdccf4c7bf49ec74d@ec2-3-229-155-151.compute-1.amazonaws.com:8989"
r = redis.from_url(REDIS_URL)

keys = r.keys()

with Session(engine) as session:
    for key in keys:
        thread_id = key.decode("utf-8")
        result = session.exec(select(Thread).where(Thread.id == thread_id))
        if result.first() is None:
            print(f"Adding thread {thread_id} to database")
            session.add(
                Thread(
                    id=thread_id,
                    title="legacy",
                    url=f"https://www.flyertalk.com/forum/{r.get(key).decode('utf-8')}",
                    started="legacy",
                    notified=True,
                )
            )
    session.commit()
