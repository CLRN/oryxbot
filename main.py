import asyncio
import json
import os
from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from io import BytesIO
from itertools import product, groupby, zip_longest
from tempfile import NamedTemporaryFile
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont
from aiobotocore.session import get_session
from aiohttp import ClientSession
from botocore.exceptions import ClientError
from dateutil.parser import parse as parse_dt
from tweepy import Client, API, OAuthHandler

from parser import parse_losses, Loss

URLS = {"https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-ukrainian.html": "ukrainian",
        "https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html": "russian"}
WAYBACK_URL = "https://archive.org/wayback/available"
S3_PATH = os.getenv('S3_PATH', 'oryx/last.json')


async def compare_with_last(s3) -> List[Tuple[str, Loss]]:
    try:
        response = await s3.get_object(Bucket=os.environ['S3_BUCKET'], Key=S3_PATH)
        async with response['Body'] as stream:
            last_data = json.loads(await stream.read())
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            last_data = {k: [] for k in URLS.values()}
        else:
            raise

    async with ClientSession() as session:
        async def _get(url: str):
            async with session.get(url) as r:
                return await r.content.read()

        bodies = await asyncio.gather(*[_get(url) for url in URLS.keys()])

    diff_losses = list()
    new_losses = list()
    for body, country in zip(bodies, URLS.values()):
        previous = set(map(lambda x: Loss(**x), last_data[country]))
        new = list(parse_losses(body))
        new_losses.append(list(map(asdict, new)))

        for item in new:
            if item not in previous:
                diff_losses.append((country, item))

    await s3.put_object(
        Bucket=os.environ['S3_BUCKET'],
        Key=S3_PATH,
        Body=BytesIO(json.dumps(dict(zip(URLS.values(), new_losses))).encode())
    )

    return diff_losses


async def compare_against_date(from_dt: date) -> Tuple[List[Tuple[str, Loss]], datetime]:
    """
    Fetches both dates from cache and compare
    :param from_dt: date from
    :return: list of losses
    """
    async with ClientSession(raise_for_status=True) as session:
        async def _get(url: str, dt: date):
            if dt is None:
                async with session.get(url) as r:
                    return await r.content.read(), datetime.utcnow()

            async with session.get(WAYBACK_URL, params={"url": url, "timestamp": dt.strftime("%Y%m%d")}) as r:
                data = await r.json()
                closest = data.get('archived_snapshots', {}).get('closest', {})
                if closest['status'] != "200":
                    raise Exception(f"Unable to retrieve snapshot: {data}")
            async with session.get(closest['url']) as r:
                return await r.read(), parse_dt(closest['timestamp'])

        jobs = list()
        for link, date_time in product(URLS.keys(), [from_dt, None]):
            jobs.append(_get(link, date_time))

        bodies = await asyncio.gather(*jobs)

    parts = [[bodies[i * 2][0], bodies[i * 2 + 1][0]] for i in range(len(bodies) // 2)]
    diff_losses = list()
    for country, data in zip(URLS.values(), parts):
        old, new = list(map(parse_losses, data))
        old = set(old)
        diff_losses.extend([(country, item) for item in new if item not in old])

    return diff_losses, min(map(lambda x: x[1], bodies))


async def calc_and_publish_delta():
    async with get_session().create_client('s3',
                                           aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                                           aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                                           endpoint_url=os.environ['AWS_ENDPOINT'],
                                           use_ssl=True) as s3:
        losses = await compare_with_last(s3)

    client = Client(
        consumer_key=os.environ['CONSUMER_KEY'],
        consumer_secret=os.environ['CONSUMER_SECRET'],
        access_token=os.environ['ACCESS_TOKEN'],
        access_token_secret=os.environ['ACCESS_TOKEN_SECRET'],
    )
    for country, loss in losses:
        print(country, loss)
        try:
            client.create_tweet(
                text=f"{country} {loss.type} {loss.status}: {loss.link}",
            )
        except Exception as e:
            print(e)


def text_to_image(
        items: List[List[str]],
        font_filepath: str,
        font_size: int,
        color: Tuple[int, int, int],
        background: Tuple[int, int, int],
) -> Image:
    countries = max(map(len, items))
    font = ImageFont.truetype(font_filepath, size=font_size)

    max_y = 0
    max_x = 0
    offset = 10
    offsets = list()
    lines_to_draw = list()
    for idx in range(countries):
        lines = [line[idx] or '' if len(line) > idx else '' for line in items]

        offsets.append(offset)
        lines_to_draw.append(lines)

        x, y = font.getsize_multiline("\n".join(lines))
        offset += x
        offset += 20
        max_x = max(max_x, offset)
        max_y = max(max_y, y)

    img = Image.new("RGB", (max_x, max_y + 30), color=background)

    draw = ImageDraw.Draw(img)
    for offset, lines in zip(offsets, lines_to_draw):
        draw_point = (offset, 0)
        draw.multiline_text(draw_point, "\n".join(lines), font=font, fill=color, align="left")

    return img


async def publish_date_diff(losses: List[Tuple[str, Loss]], date_: date):
    country_items = defaultdict(list)
    for country, country_data in groupby(losses, lambda x: x[0]):
        data = list(map(lambda x: x[1], country_data))
        for vehicle, vehicle_data in groupby(data, lambda x: x.type):
            vehicle_data = list(vehicle_data)
            status_items = [f"{vehicle} total: {len(vehicle_data)}"]
            for status, status_data in groupby(vehicle_data, lambda x: x.status):
                status_items.append(f"{status}: {len(list(status_data))}")
            country_items[country].append(f", ".join(status_items))

    items = [[f"Losses between {date_.isoformat()} and {datetime.utcnow().isoformat()}"],
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
    client.create_tweet(text='', media_ids=[ret.media_id_string])


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--delta-days", help="Publish summary of losses goign back N days", type=int)
    args = parser.parse_args()

    if args.delta_days:
        diff, date = asyncio.run(compare_against_date(datetime.utcnow().date() - timedelta(days=args.delta_days)))
        asyncio.run(publish_date_diff(diff, date))
    else:
        asyncio.run(calc_and_publish_delta())
