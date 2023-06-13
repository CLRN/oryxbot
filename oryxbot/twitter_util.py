import logging
import os
from collections import defaultdict
from datetime import date, datetime
from itertools import groupby, zip_longest
from tempfile import NamedTemporaryFile
from typing import List, Tuple

from aiohttp import ClientSession
from tweepy import Client, API, OAuthHandler

from oryxbot.image_resolver import resolve
from oryxbot.parser import Loss
from oryxbot.txt2image import text_to_image


def publish_date_diff(losses: List[Tuple[str, Loss]], date_: date):
    if not losses:
        return

    country_items = defaultdict(list)
    for country, country_data in groupby(losses, lambda x: x[0]):
        data = list(map(lambda x: x[1], country_data))
        for vehicle, vehicle_data in groupby(data, lambda x: x.type):
            vehicle_data = list(vehicle_data)
            status_items = [f"{vehicle} total: {len(vehicle_data)}"]
            for status, status_data in groupby(vehicle_data, lambda x: x.status):
                status_items.append(f"{status}: {len(list(status_data))}")
            country_items[country].append(f", ".join(status_items))

    now = datetime.utcnow()
    interval_str = f"{now - date_}".split(".")[0]
    items = [[f"Losses for {interval_str} between {date_.isoformat()} and {now.isoformat()}"],
             [f"{country.capitalize()} losses: {len(data)}" for country, data in country_items.items()]]

    sorted_by_name = {c: sorted(data) for c, data in country_items.items()}

    for vals in zip_longest(*sorted_by_name.values()):
        items.append(list(vals))

    auth = OAuthHandler(consumer_key=os.environ['CONSUMER_KEY'], consumer_secret=os.environ['CONSUMER_SECRET'])
    auth.set_access_token(key=os.environ['ACCESS_TOKEN'], secret=os.environ['ACCESS_TOKEN_SECRET'])
    api = API(auth)

    client = Client(
        consumer_key=os.environ['CONSUMER_KEY'],
        consumer_secret=os.environ['CONSUMER_SECRET'],
        access_token=os.environ['ACCESS_TOKEN'],
        access_token_secret=os.environ['ACCESS_TOKEN_SECRET'],
    )

    with NamedTemporaryFile(suffix='.png') as temp_file:
        img = text_to_image(
            items=items,
            font_filepath="fonts/arial.ttf",
            font_size=18,
            color=(240, 230, 10),
            background=(50, 50, 50)
        )
        img.save(temp_file.name)
        ret = api.media_upload(filename=temp_file.name)
    client.create_tweet(text=items[0][0], media_ids=[ret.media_id_string])


async def publish_losses(losses: List[Tuple[str, Loss]]):
    client = Client(
        consumer_key=os.environ['CONSUMER_KEY'],
        consumer_secret=os.environ['CONSUMER_SECRET'],
        access_token=os.environ['ACCESS_TOKEN'],
        access_token_secret=os.environ['ACCESS_TOKEN_SECRET'],
    )
    async with ClientSession() as session:
        for country, loss in losses:
            logging.info(f"{country=}, {loss=}")
            try:
                ids = await resolve(session, loss.link)
                # client.create_tweet(
                #     text=f"{country} {loss.type} {loss.status}: {loss.link}",
                #     media_ids=
                # )
            except Exception:
                logging.exception(f"Failed to publish diff")
