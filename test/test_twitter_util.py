from mock import patch

from oryxbot.twitter_util import publish_losses, Loss


@patch('oryxbot.twitter_util.Client')
def test_publish_losses(client):
    with patch('oryxbot.twitter_util.os.environ'):
        publish_losses([('ru', Loss(type='test', status='ok', number=1, link='http://foo'))])


@patch('oryxbot.twitter_util.Client')
def test_publish_losses_exception(client):
    client.create_tweet.side_effect = [Exception("fail")]
    with patch('oryxbot.twitter_util.os.environ'):
        publish_losses([('ru', Loss(type='test', status='fail', number=1, link='http://foo'))])
