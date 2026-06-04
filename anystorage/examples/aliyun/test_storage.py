import os
import time

import pytest
from dotenv import load_dotenv
from pathlib import Path

from anystorage.contrib.aliyun import AliyunStorage
from anystorage.contrib.aliyun import AliyunBucket


# 测试用的 Bucket 名称，避免与生产环境冲突
TEST_BUCKET_NAME = "test-storage-" + str(int(time.time()))

# 项目根目录下的 .env.aliyun
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env.aliyun"
load_dotenv(_ENV_FILE)


@pytest.fixture(scope="module")
def storage() -> AliyunStorage:
    """创建 AliyunStorage 实例，模块级别共享。"""
    return AliyunStorage(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
        endpoint=os.getenv("ALIYUN_ENDPOINT", ""),
        region=os.getenv("ALIYUN_REGION", ""),
        use_ssl=os.getenv("ALIYUN_ENDPOINT_SSL", "false").lower() in ("true", "1", "yes"),
    )


# ==================== Init ====================

class TestStorageInit:
    """AliyunStorage 初始化相关测试。"""

    @pytest.mark.order(1)
    def test_init_with_valid_config(self):
        """使用有效配置初始化应成功。"""
        s = AliyunStorage(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("ALIYUN_ENDPOINT", ""),
            region=os.getenv("ALIYUN_REGION", ""),
        )
        assert s.auth is not None
        assert s.service is not None
        assert s.endpoint.startswith("http")

    @pytest.mark.order(2)
    def test_init_missing_credentials(self):
        """缺少必要配置时应抛出 ValueError。"""
        with pytest.raises(ValueError, match="环境变量配置错误"):
            AliyunStorage(
                access_key_id="",
                access_key_secret="",
                endpoint="",
            )

    @pytest.mark.order(3)
    def test_init_ssl_endpoint(self):
        """use_ssl=True 时 endpoint 应以 https:// 开头。"""
        s = AliyunStorage(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            endpoint="oss-cn-shanghai.aliyuncs.com",
            use_ssl=True,
        )
        assert s.endpoint.startswith("https://")

    @pytest.mark.order(4)
    def test_init_no_ssl_endpoint(self):
        """use_ssl=False 时 endpoint 应以 http:// 开头。"""
        s = AliyunStorage(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            endpoint="oss-cn-shanghai.aliyuncs.com",
            use_ssl=False,
        )
        assert s.endpoint.startswith("http://")
        assert not s.endpoint.startswith("https://")

    @pytest.mark.order(5)
    def test_init_endpoint_already_has_scheme(self):
        """endpoint 已带协议前缀时不应重复添加。"""
        s = AliyunStorage(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            endpoint="https://oss-cn-shanghai.aliyuncs.com",
            use_ssl=False,  # 即使 use_ssl=False，已有 https 也不应覆盖
        )
        assert s.endpoint.startswith("https://")


# ==================== Create ====================

class TestStorageCreate:
    """AliyunStorage 创建 Bucket 相关测试。"""

    @pytest.mark.order(6)
    def test_ensure_bucket_creates_new(self, storage: AliyunStorage):
        """ensure_bucket 应创建一个新的 Bucket。"""
        # 测试名称含时间戳，不可能存在
        assert not storage.bucket_exists(TEST_BUCKET_NAME)

        bucket = storage.ensure_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        assert isinstance(bucket, AliyunBucket)
        assert bucket.name == TEST_BUCKET_NAME
        assert storage.bucket_exists(TEST_BUCKET_NAME)


# ==================== Read ====================

class TestStorageRead:
    """AliyunStorage 读取相关测试。"""

    @pytest.mark.order(7)
    def test_bucket_exists_true(self, storage: AliyunStorage):
        """bucket_exists 对已存在的 Bucket 应返回 True。"""
        assert storage.bucket_exists(TEST_BUCKET_NAME) is True

    @pytest.mark.order(8)
    def test_bucket_exists_false(self, storage: AliyunStorage):
        """bucket_exists 对不存在的 Bucket 应返回 False。"""
        assert storage.bucket_exists("non-existent-bucket-xyz-99999") is False

    @pytest.mark.order(9)
    def test_get_bucket_found(self, storage: AliyunStorage):
        """get_bucket 对已存在的 Bucket 应返回 AliyunBucket 实例。"""
        bucket = storage.get_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        assert isinstance(bucket, AliyunBucket)
        assert bucket.name == TEST_BUCKET_NAME

    @pytest.mark.order(11)
    def test_get_bucket_not_found(self, storage: AliyunStorage):
        """get_bucket 对不存在的 Bucket 应返回 None。"""
        bucket = storage.get_bucket("non-existent-bucket-xyz-99999")
        assert bucket is None

    @pytest.mark.order(12)
    def test_list_buckets(self, storage: AliyunStorage):
        """buckets 属性应返回包含测试 Bucket 的列表。"""
        buckets = storage.buckets
        assert isinstance(buckets, list)
        assert len(buckets) > 0
        assert any(b.name == TEST_BUCKET_NAME for b in buckets)


# ==================== Delete ====================

class TestStorageDelete:
    """AliyunStorage 删除 Bucket 相关测试。"""

    @pytest.mark.order(13)
    def test_delete_bucket_via_bucket_instance(self, storage: AliyunStorage):
        """通过 AliyunBucket.delete() 删除后，bucket_exists 应返回 False。"""
        bucket = storage.get_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        bucket.delete()
        assert storage.bucket_exists(TEST_BUCKET_NAME) is False

    @pytest.mark.order(14)
    def test_ensure_and_delete_lifecycle(self, storage: AliyunStorage):
        """完整的创建→确认存在→删除→确认不存在生命周期。"""
        lifecycle_name = f"{TEST_BUCKET_NAME}-lifecycle"

        # 创建
        bucket = storage.ensure_bucket(lifecycle_name)
        assert bucket is not None
        assert storage.bucket_exists(lifecycle_name)

        # 删除
        bucket.delete()
        assert storage.bucket_exists(lifecycle_name) is False
