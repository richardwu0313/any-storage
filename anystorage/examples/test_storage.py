import os

from dotenv import load_dotenv
from pathlib import Path
import pytest

from anystorage.storage import create_storage
from anystorage.enums import StorageEnum


# 项目根目录下的 .env.minio
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)


class TestStorageFactory:

    def test_aliyun(self):
        storage_cls = create_storage(StorageEnum.ALIYUN)
        storage = storage_cls(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("ALIYUN_ENDPOINT", ""),
            region=os.getenv("ALIYUN_REGION", ""),
            use_ssl=os.getenv("ALIYUN_ENDPOINT_SSL", "false").lower() in ("true", "1", "yes"),
        )
        assert storage is not None

    def test_minio(self):
        storage_cls = create_storage(StorageEnum.MINIO)
        storage = storage_cls(
            access_key_id=os.getenv("MINIO_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("MINIO_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("MINIO_ENDPOINT", ""),
            connect_timeout=int(os.getenv("MINIO_CONNECT_TIMEOUT", 10)),
            read_timeout=int(os.getenv("MINIO_READ_TIMEOUT", 10)),
            use_ssl=os.getenv("MINIO_ENDPOINT_SSL", "false").lower() in ("true", "1", "yes"),
        )
        assert storage is not None
