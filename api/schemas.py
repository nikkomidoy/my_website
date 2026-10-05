import datetime

import msgspec


class PostQuery(msgspec.Struct):
    tag: str = ""
    limit: int = 20


class PostOut(msgspec.Struct):
    title: str
    slug: str
    url: str
    excerpt: str
    tags: list[str]
    published_at: datetime.datetime | None
