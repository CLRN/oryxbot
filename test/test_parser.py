import os.path

from oryxbot.parser import parse_losses, Loss


def test_parser():
    path = os.path.join(os.path.dirname(__file__), 'last.html')
    before = list(parse_losses(open(path, 'rb').read()))
    after = before.copy()
    del before[123]

    prev = set(before)
    diffed = []
    for item in after:
        if item not in prev:
            diffed.append(item)

    assert diffed == [Loss(type='T-64BV', status='damaged', number=4,
                           link='https://i.postimg.cc/L52GF2Ln/1001-unkn-tank-dam-23-02-23.jpg')]
