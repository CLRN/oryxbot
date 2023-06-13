from datetime import date, datetime

import pytest
from mock import MagicMock

from oryxbot.archive_util import url_snapshot


@pytest.mark.asyncio
async def test_snapshot_with_date_success():
    session = MagicMock()

    first_call = MagicMock()
    first_call.__aenter__.return_value.json.return_value = {
        'archived_snapshots': {'closest': {'status': '200', 'timestamp': '20230506111213', 'url': 'http://closest'}}
    }

    second_call = MagicMock()
    second_call.__aenter__.return_value.read.return_value = b'body'

    session.get.side_effect = [first_call, second_call]

    assert await url_snapshot(session, 'http://test', date(2023, 1, 1)) == (b'body', datetime(2023, 5, 6, 11, 12, 13))


@pytest.mark.asyncio
async def test_snapshot_with_date_fail():
    session = MagicMock()

    first_call = MagicMock()
    first_call.__aenter__.return_value.json.return_value = {
        'archived_snapshots': {'closest': {'status': '404', 'timestamp': '20230506111213', 'url': 'http://closest'}}
    }

    session.get.side_effect = [first_call]

    with pytest.raises(Exception):
        await url_snapshot(session, 'http://test', date(2023, 1, 1))


@pytest.mark.asyncio
async def test_snapshot_without_date_success():
    session = MagicMock()

    second_call = MagicMock()
    second_call.__aenter__.return_value.read.return_value = b'body'

    session.get.side_effect = [second_call]

    assert (await url_snapshot(session, 'http://test', None))[0] == b'body'
