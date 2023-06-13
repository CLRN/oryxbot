from mock import patch

from oryxbot.twitterutil import publish_losses, Loss


@patch('oryxbot.twitterutil.Client')
def test_publish_losses(client):
    with patch('oryxbot.twitterutil.os.environ'):
        publish_losses([('ru', Loss(type='test', status='ok', number=1, link='http://foo'))])


@patch('oryxbot.twitterutil.Client')
def test_publish_losses_exception(client):
    client.create_tweet.side_effect = [Exception("fail")]
    with patch('oryxbot.twitterutil.os.environ'):
        publish_losses([('ru', Loss(type='test', status='fail', number=1, link='http://foo'))])
