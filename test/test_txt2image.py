import os

from oryxbot.txt2image import text_to_image


def test_text_to_image():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'arial.ttf')
    img = text_to_image([["test"]], path, 10, (200, 200, 200), (0, 0, 0))
    assert img.size == (46, 41)
