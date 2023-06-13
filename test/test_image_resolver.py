from io import BytesIO

import pytest
from PIL import Image
from mock import patch, AsyncMock, MagicMock

from oryxbot.image_resolver import resolve


@pytest.mark.asyncio
@patch('oryxbot.image_resolver.os.environ')
async def test_resolve_twitter_link(env):
    session = MagicMock()
    first_call = MagicMock()
    second_call = MagicMock()

    first_call.__aenter__.return_value.real_url = MagicMock(host='twitter.com',
                                                            path='/dsadsa/dsa/status/1234')
    second_call.__aenter__.return_value.json.return_value = {'includes': {'media': [{'media_key': 'key_1'}]}}

    session.get.side_effect = [first_call, second_call]
    assert await resolve(session, 'https://twitter.com/UAWeapons/status/1667622822594617344') == ['key_1']


@pytest.mark.asyncio
@patch('oryxbot.image_resolver.os.environ')
@patch('oryxbot.image_resolver.OAuthHandler')
@patch('oryxbot.image_resolver.API')
async def test_resolve_image_direct_link(api, oauth, env):
    session = MagicMock()
    first_call = MagicMock()
    second_call = MagicMock()

    img = Image.new('RGB', (10, 10))
    buffer = BytesIO()
    img.save(buffer, format='png')
    buffer.seek(0)

    api.return_value.media_upload.return_value.media_id_string = 'key_2'

    first_call.__aenter__.return_value.real_url = MagicMock(host='hosting.com')
    first_call.__aenter__.return_value.read = AsyncMock(return_value=buffer.read())
    second_call.__aenter__.return_value.json.return_value = {'includes': {'media': [{'media_key': 'key_1'}]}}

    session.get.side_effect = [first_call, second_call]
    assert await resolve(session, 'https://twitter.com/UAWeapons/status/1667622822594617344') == ['key_2']


@pytest.mark.asyncio
@patch('oryxbot.image_resolver.os.environ')
@patch('oryxbot.image_resolver.OAuthHandler')
@patch('oryxbot.image_resolver.API')
async def test_resolve_image_hosting(api, oauth, env):
    session = MagicMock()
    first_call = MagicMock()
    second_call = MagicMock()

    html = b"<!DOCTYPE HTML><html><img src='test' id='main-image'/></html>"

    img = Image.new('RGB', (10, 10))
    buffer = BytesIO()
    img.save(buffer, format='png')
    buffer.seek(0)

    first_call.__aenter__.return_value.real_url = MagicMock(host='hosting.com')
    first_call.__aenter__.return_value.read = AsyncMock(return_value=html)
    second_call.__aenter__.return_value.read = AsyncMock(return_value=buffer.read())
    api.return_value.media_upload.return_value.media_id_string = 'key_3'

    session.get.side_effect = [first_call, second_call]
    assert await resolve(session, 'https://twitter.com/UAWeapons/status/1667622822594617344') == ['key_3']


@pytest.mark.asyncio
@patch('oryxbot.image_resolver.os.environ')
async def test_resolve_error(env):
    session = MagicMock()
    first_call = MagicMock()
    second_call = MagicMock()

    first_call.__aenter__.return_value.real_url = MagicMock(host='twitter.com',
                                                            path='/dsadsa/dsa/status/1234')
    second_call.__aenter__.return_value.json.return_value = {'error': 'fail'}

    session.get.side_effect = [first_call, second_call]
    assert await resolve(session, 'https://twitter.com/UAWeapons/status/1667622822594617344') == []
