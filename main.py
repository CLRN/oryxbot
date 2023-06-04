import asyncio
import json
import os
from dataclasses import asdict
from io import BytesIO
from typing import List, Tuple

from aiobotocore.session import get_session
from aiohttp import ClientSession
from botocore.exceptions import ClientError
from tweepy import Client

from parser import parse_losses, Loss

URLS = {"https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-ukrainian.html": "ukrainian",
        "https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html": "russian"}
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


async def main():
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
        client.create_tweet(
            text=f"{country} {loss.type} {loss.status}: {loss.link}",
        )


if __name__ == '__main__':
    asyncio.run(main())
