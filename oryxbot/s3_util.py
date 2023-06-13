import json
import os
from contextlib import asynccontextmanager
from io import BytesIO

from aiobotocore.session import get_session
from botocore.exceptions import ClientError


@asynccontextmanager
async def s3_client():
    async with get_session().create_client('s3',
                                           aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                                           aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                                           endpoint_url=os.environ['AWS_ENDPOINT'],
                                           use_ssl=True) as s3:

        async def _get(path: str) -> dict:
            try:
                response = await s3.get_object(Bucket=os.environ['S3_BUCKET'], Key=path)
                async with response['Body'] as stream:
                    return json.loads(await stream.read())
            except ClientError as ex:
                if ex.response['Error']['Code'] == 'NoSuchKey':
                    return {}
                else:
                    raise

        async def _put(path: str, data: dict):
            await s3.put_object(
                Bucket=os.environ['S3_BUCKET'],
                Key=path,
                Body=BytesIO(json.dumps(data).encode())
            )

        yield _get, _put
