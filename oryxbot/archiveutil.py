from __future__ import annotations

import logging
from datetime import date, datetime

from aiohttp import ClientSession
from dateutil.parser import parse as parse_dt
from waybackpy import Url

WAYBACK_URL = "https://archive.org/wayback/available"


async def url_snapshot(session: ClientSession, url: str, dt: date | None):
    if dt is None:
        async with session.get(url) as r:
            return await r.read(), datetime.utcnow()

    async with session.get(WAYBACK_URL, params={"url": url, "timestamp": dt.strftime("%Y%m%d")}) as r:
        data = await r.json()
        closest = data.get('archived_snapshots', {}).get('closest', {})
        if closest['status'] != "200":
            raise Exception(f"Unable to retrieve snapshot: {data}")
    async with session.get(closest['url']) as r:
        return await r.read(), parse_dt(closest['timestamp'])


def save_url(url: str):
    new = Url(
        url=url,
        user_agent="Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
    ).save()
    logging.info(f"Saved {url} to {new}")
