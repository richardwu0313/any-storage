import os
import time

import pytest
from dotenv import load_dotenv
from pathlib import Path

from anystorage.contrib.minio_storage import MinioStorage
from anystorage.contrib.minio_storage import MinioBucket


# 测试用的 Bucket 名称，避免与生产环境冲突
TEST_BUCKET_NAME = "test-storage-" + str(int(time.time()))

# 项目根目录下的 .env.minio
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env.minio"
load_dotenv(_ENV_FILE)


@pytest.fixture(scope="module")
def storage() -> MinioStorage:
    """创建 MinioStorage 实例，模块级别共享。"""
    return MinioStorage(
        access_key_id=os.getenv("MINIO_ACCESS_KEY_ID", ""),
        access_key_secret=os.getenv("MINIO_ACCESS_KEY_SECRET", ""),
        endpoint=os.getenv("MINIO_ENDPOINT", ""),
        use_ssl=os.getenv("MINIO_ENDPOINT_SSL", "false").lower() in ("true", "1", "yes"),
    )


# ==================== Init ====================

class TestStorageInit:
    """MinioStorage 初始化相关测试。"""

    @pytest.mark.order(1)
    def test_init_with_valid_config(self):
        """使用有效配置初始化应成功。"""
        s = MinioStorage(
            access_key_id=os.getenv("MINIO_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("MINIO_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("MINIO_ENDPOINT", ""),
            use_ssl=False,
        )
        assert s._minio_storage is not None
        assert s.endpoint is not None

    @pytest.mark.order(2)
    def test_init_instance_attributes(self):
        """初始化后 connect_timeout 和 read_timeout 应为实例属性。"""
        s = MinioStorage(
            access_key_id=os.getenv("MINIO_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("MINIO_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("MINIO_ENDPOINT", ""),
            use_ssl=False,
        )
        assert hasattr(s, "connect_timeout")
        assert hasattr(s, "read_timeout")
        assert isinstance(s.connect_timeout, int)
        assert isinstance(s.read_timeout, int)

    @pytest.mark.order(3)
    def test_init_ssl(self):
        """use_ssl=True 时 Minio 客户端应使用安全连接。"""
        s = MinioStorage(
            access_key_id=os.getenv("MINIO_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("MINIO_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("MINIO_ENDPOINT", ""),
            use_ssl=True,
        )
        assert s._minio_storage is not None
        assert s.use_ssl is True


# ==================== Create ====================

class TestStorageCreate:
    """MinioStorage 创建 Bucket 相关测试。"""

    @pytest.mark.order(4)
    def test_ensure_bucket_creates_new(self, storage: MinioStorage):
        """ensure_bucket 应创建一个新的 Bucket。"""
        # 测试名称含时间戳，不可能存在
        assert not storage.bucket_exists(TEST_BUCKET_NAME)

        bucket = storage.ensure_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        assert isinstance(bucket, MinioBucket)
        assert bucket.name == TEST_BUCKET_NAME
        assert storage.bucket_exists(TEST_BUCKET_NAME)

    @pytest.mark.order(5)
    def test_ensure_bucket_idempotent(self, storage: MinioStorage):
        """ensure_bucket 对已存在的 Bucket 应幂等返回。"""
        bucket1 = storage.ensure_bucket(TEST_BUCKET_NAME)
        bucket2 = storage.ensure_bucket(TEST_BUCKET_NAME)
        assert bucket1 is not None
        assert bucket2 is not None
        assert bucket1.name == bucket2.name


# ==================== Read ====================

class TestStorageRead:
    """MinioStorage 读取相关测试。"""

    @pytest.mark.order(6)
    def test_bucket_exists_true(self, storage: MinioStorage):
        """bucket_exists 对已存在的 Bucket 应返回 True。"""
        assert storage.bucket_exists(TEST_BUCKET_NAME) is True

    @pytest.mark.order(7)
    def test_bucket_exists_false(self, storage: MinioStorage):
        """bucket_exists 对不存在的 Bucket 应返回 False。"""
        assert storage.bucket_exists("non-existent-bucket-xyz-99999") is False

    @pytest.mark.order(8)
    def test_get_bucket_found(self, storage: MinioStorage):
        """get_bucket 对已存在的 Bucket 应返回 MinioBucket 实例。"""
        bucket = storage.get_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        assert isinstance(bucket, MinioBucket)
        assert bucket.name == TEST_BUCKET_NAME

    @pytest.mark.order(9)
    def test_get_bucket_not_found(self, storage: MinioStorage):
        """get_bucket 对不存在的 Bucket 应返回 None。"""
        bucket = storage.get_bucket("non-existent-bucket-xyz-99999")
        assert bucket is None

    @pytest.mark.order(10)
    def test_list_buckets(self, storage: MinioStorage):
        """buckets 方法应返回包含测试 Bucket 的列表。"""
        buckets = storage.buckets()
        assert isinstance(buckets, list)
        assert len(buckets) > 0
        assert any(b.name == TEST_BUCKET_NAME for b in buckets)


# ==================== Delete ====================

class TestStorageDelete:
    """MinioStorage 删除 Bucket 相关测试。"""

    @pytest.mark.order(11)
    def test_delete_bucket_via_bucket_instance(self, storage: MinioStorage):
        """通过 MinioBucket.delete() 删除后，bucket_exists 应返回 False。"""
        bucket = storage.get_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        bucket.delete()
        assert storage.bucket_exists(TEST_BUCKET_NAME) is False

    @pytest.mark.order(12)
    def test_ensure_and_delete_lifecycle(self, storage: MinioStorage):
        """完整的创建→确认存在→删除→确认不存在生命周期。"""
        lifecycle_name = f"{TEST_BUCKET_NAME}-lifecycle"

        # 创建
        bucket = storage.ensure_bucket(lifecycle_name)
        assert bucket is not None
        assert storage.bucket_exists(lifecycle_name)

        # 删除
        bucket.delete()
        assert storage.bucket_exists(lifecycle_name) is False
