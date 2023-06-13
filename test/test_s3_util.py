import pytest
from mock import patch, AsyncMock, MagicMock

from oryxbot.s3_util import s3_client
from botocore.exceptions import ClientError

@pytest.mark.asyncio
@patch('oryxbot.s3_util.get_session')
@patch('oryxbot.s3_util.os.environ')
async def test_s3_get(env, session):
    client = AsyncMock()
    session.return_value.create_client.return_value = AsyncMock(__aenter__=client)

    content = AsyncMock(return_value=b'{"test": 123}')
    client.return_value.get_object.return_value.__getitem__.return_value.__aenter__.return_value.read = content

    async with s3_client() as (get, put):
        assert await get('test') == {"test": 123}


@pytest.mark.asyncio
@patch('oryxbot.s3_util.get_session')
@patch('oryxbot.s3_util.os.environ')
async def test_s3_get_no_data(env, session):
    client = AsyncMock()
    session.return_value.create_client.return_value = AsyncMock(__aenter__=client)

    response = MagicMock()
    response.__getitem__.return_value.__getitem__.return_value = 'NoSuchKey'
    client.return_value.get_object.side_effect = ClientError(response, MagicMock())

    async with s3_client() as (get, put):
        assert await get('test') == {}


@pytest.mark.asyncio
@patch('oryxbot.s3_util.get_session')
@patch('oryxbot.s3_util.os.environ')
async def test_s3_get_exception(env, session):
    client = AsyncMock()
    session.return_value.create_client.return_value = AsyncMock(__aenter__=client)

    response = MagicMock()
    response.__getitem__.return_value.__getitem__.return_value = 'Fail'
    client.return_value.get_object.side_effect = ClientError(response, MagicMock())

    async with s3_client() as (get, put):
        with pytest.raises(Exception):
            await get('test')


@pytest.mark.asyncio
@patch('oryxbot.s3_util.get_session')
@patch('oryxbot.s3_util.os.environ')
async def test_s3_put(env, session):
    client = AsyncMock()
    session.return_value.create_client.return_value = AsyncMock(__aenter__=client)

    async with s3_client() as (get, put):
        await put('test', {"test": 123})

    assert client.return_value.put_object.called