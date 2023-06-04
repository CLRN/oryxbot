import random

from parser import parse_losses


def test_parser():
    before = list(parse_losses(open('last.html', 'rb').read()))
    after = before.copy()
    del before[random.randint(0, len(before))]

    prev = set(before)
    diffed = []
    for item in after:
        if item not in prev:
            diffed.append(item)

    assert diffed
