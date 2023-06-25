from mock import patch
import pytest

from oryxbot.twitter_util import publish_losses, Loss


@pytest.mark.asyncio
@patch('oryxbot.twitter_util.Client')
async def test_publish_losses(client):
    with patch('oryxbot.twitter_util.os.environ'):
        await publish_losses([('ru', Loss(type='test', status='ok', number=1, link='http://foo'))])


@pytest.mark.asyncio
@patch('oryxbot.twitter_util.Client')
async def test_publish_losses_exception(client):
    client.create_tweet.side_effect = [Exception("fail")]
    with patch('oryxbot.twitter_util.os.environ'):
        await publish_losses([('ru', Loss(type='test', status='fail', number=1, link='http://foo'))])
