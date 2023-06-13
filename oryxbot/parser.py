import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterator

from lxml.html import HtmlElement, etree, html_parser


class Status(Enum):
    Destroyed = 'destroyed'
    Captured = 'captured'
    Damaged = 'damaged'
    Abandoned = 'abandoned'
    Sunk = 'sunk'
    Scuttled = 'scuttled'


@dataclass(frozen=True, eq=True)
class Loss:
    type: str
    status: str
    number: int
    link: str


def _extract_tails(root: HtmlElement) -> str:
    if root is None:
        return ''
    res = root.tail or ''
    for child in root.getchildren():
        res += _extract_tails(child)
    return res


def parse_losses(body: bytes) -> Iterator[Loss]:
    doc: HtmlElement = etree.fromstring(body, html_parser)
    links = doc.findall(".//a")
    link: HtmlElement
    for link in links:
        if not link.text or not link.text.startswith('(') or not link.text.endswith(')'):
            continue

        parent: HtmlElement = link
        while parent is not None and parent.tag != 'li':
            parent: HtmlElement = parent.getparent()

        txt = _extract_tails(parent).strip()
        match = re.match(r'\d+\W+(.+)$', txt)
        if not match:
            continue

        for item in re.findall(r'\d+', link.text):
            status = next(filter(lambda x: x[1].value in link.text, enumerate(Status)))[1]
            yield Loss(
                type=match.group(1).strip(':'),
                status=status.value,
                number=int(item),
                link='http' + link.attrib['href'].strip().split('http')[-1]
            )
