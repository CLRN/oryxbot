import asyncio
import logging
import os
from argparse import ArgumentParser
from dataclasses import asdict
from datetime import date, datetime, timedelta
from itertools import product
from typing import List, Tuple

from aiohttp import ClientSession

from oryxbot.archive_util import save_url, url_snapshot
from oryxbot.parser import parse_losses, Loss
from oryxbot.s3_util import s3_client
from oryxbot.twitter_util import publish_date_diff, publish_losses

URLS = {"https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-ukrainian.html": "ukrainian",
        "https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html": "russian"}

S3_PATH_LAST = os.getenv('S3_PATH_LAST', 'oryx/last.json')
S3_PATH_DELTA = os.getenv('S3_PATH_DELTA', f'oryx/{datetime.utcnow().isoformat()}.json')


async def compare_with_last_and_publish() -> List[Tuple[str, Loss]]:
    async with ClientSession() as session:
        async def _get(url: str):
            async with session.get(url) as r:
                return await r.content.read()

        bodies = await asyncio.gather(*[_get(url) for url in URLS.keys()])

    async with s3_client() as (get, put):
        last_data = await get(S3_PATH_LAST)

        diff_losses = list()
        new_losses = list()
        for body, country in zip(bodies, URLS.values()):
            previous = set(map(lambda x: Loss(**x), last_data.get(country, [])))
            new = list(parse_losses(body))
            new_losses.append(list(map(asdict, new)))

            for item in new:
                if item not in previous:
                    diff_losses.append((country, item))

        await put(S3_PATH_LAST, dict(zip(URLS.values(), new_losses)))

        if diff_losses:
            await publish_losses(diff_losses)
            await put(S3_PATH_DELTA, list(map(lambda x: [x[0], asdict(x[1])], diff_losses)))

    return diff_losses


async def compare_against_date(from_dt: date) -> Tuple[List[Tuple[str, Loss]], datetime]:
    """
    Fetches both dates from cache and compare
    :param from_dt: date from
    :return: list of losses
    """
    async with ClientSession(raise_for_status=True) as session:
        jobs = list()
        for link, date_time in product(URLS.keys(), [from_dt, None]):
            jobs.append(url_snapshot(session, link, date_time))

        bodies = await asyncio.gather(*jobs)

    parts = [[bodies[i * 2][0], bodies[i * 2 + 1][0]] for i in range(len(bodies) // 2)]
    diff_losses = list()
    for country, data in zip(URLS.values(), parts):
        old, new = list(map(parse_losses, data))
        old = set(old)
        diff_losses.extend([(country, item) for item in new if item not in old])
    return diff_losses, min(map(lambda x: x[1], bodies))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--delta-days", help="Publish summary of losses going back N days", type=int)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    logging.getLogger().setLevel(logging.INFO)

    if args.delta_days:
        try:
            diff, date = asyncio.run(compare_against_date(datetime.utcnow().date() - timedelta(days=args.delta_days)))
            publish_date_diff(diff, date)
        except Exception:
            logging.exception(f"Failed to process diff")
        list(map(save_url, URLS.keys()))
    else:
        losses = asyncio.run(compare_with_last_and_publish())

        if losses:
            diff, dt = asyncio.run(compare_against_date(datetime.utcnow().date() - timedelta(days=1)))
            publish_date_diff(diff, dt)

            diff, dt = asyncio.run(compare_against_date(datetime.utcnow().date() - timedelta(days=7)))
            publish_date_diff(diff, dt)

            diff, dt = asyncio.run(compare_against_date(date(2023, 6, 5)))
            publish_date_diff(diff, dt)

