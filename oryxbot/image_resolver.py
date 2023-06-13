import logging
import os
from io import BytesIO
from tempfile import NamedTemporaryFile

from PIL import Image
from aiohttp import ClientSession
from lxml.html import HtmlElement, etree, html_parser
from tweepy import API, OAuthHandler

TWITTER_HOST = "twitter.com"
TWEET_PARAMS = {"tweet.fields": "lang",
                "media.fields": "url",
                "expansions": "attachments.media_keys,author_id",
                "user.fields": "username"}


async def resolve(session: ClientSession, url: str):
    result = list()
    try:
        async with session.get(url) as response:
            if response.real_url.host == TWITTER_HOST:
                parts = response.real_url.path.split("/")
                while parts and parts[0] != 'status':
                    parts.pop(0)

                url = f"https://api.twitter.com/2/tweets/{parts[1]}"
                async with session.get(
                        url,
                        headers={"Authorization": f"Bearer {os.getenv('READ_TWEET_TOKEN')}"},
                        params=TWEET_PARAMS,
                ) as response:
                    data = await response.json()
                    logging.info(f"Tweet data: {data}")
                    return [m['media_key'] for m in data['includes']['media']]

            body = await response.read()
            if body.startswith(b"<!DOCTYPE HTML>"):
                doc: HtmlElement = etree.fromstring(body, html_parser)
                links = doc.findall(".//img[@id='main-image']")
                link: HtmlElement
                for link in links:
                    result.extend(await resolve(session, link.attrib['src']))
                return result

            auth = OAuthHandler(consumer_key=os.environ['CONSUMER_KEY'],
                                consumer_secret=os.environ['CONSUMER_SECRET'])
            auth.set_access_token(key=os.environ['ACCESS_TOKEN'], secret=os.environ['ACCESS_TOKEN_SECRET'])
            api = API(auth)

            with NamedTemporaryFile(suffix='.png') as temp_file:
                img = Image.open(BytesIO(body))
                img.save(temp_file.name)
                ret = api.media_upload(filename=temp_file.name)
            result.append(ret.media_id_string)
    except Exception:
        logging.exception(f"Unable to process {url=}")
    logging.info(f"Resolved {url=} to {result}")
    return result
