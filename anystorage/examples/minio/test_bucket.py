import os
import tempfile
import time

import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

from anystorage.contrib.minio_storage import MinioStorage
from anystorage.contrib.minio_storage import MinioBucket
from anystorage.contrib.minio_storage import MinioObject


# 测试用的 Bucket 名称，避免与生产环境冲突
TEST_BUCKET_NAME = "test-bucket-" + str(int(time.time()))

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
        connect_timeout=int(os.getenv("MINIO_CONNECT_TIMEOUT", 10)),
        read_timeout=int(os.getenv("MINIO_READ_TIMEOUT", 10)),
        use_ssl=os.getenv("MINIO_ENDPOINT_SSL", "false").lower() in ("true", "1", "yes"),
    )


@pytest.fixture(scope="module")
def bucket(storage: MinioStorage) -> MinioBucket:
    """确保测试 Bucket 存在并返回实例，模块级别共享。

    测试结束后自动清理：删除 Bucket 中所有对象后删除 Bucket 本身。
    """
    bucket = storage.ensure_bucket(TEST_BUCKET_NAME)
    assert bucket is not None, f"创建测试 Bucket {TEST_BUCKET_NAME} 失败"
    yield bucket
    # teardown: Bucket 已在测试中被删除，无需清理


# ==================== Create ====================

class TestBucketCreate:
    """Bucket 创建相关测试。"""

    @pytest.mark.order(1)
    def test_ensure_bucket_creates_new(self, storage: MinioStorage):
        """ensure_bucket 应创建一个不存在的 Bucket。"""
        # 测试bucket名称中包含时间戳，不可能存在
        if storage.bucket_exists(TEST_BUCKET_NAME):
            bkt = storage.get_bucket(TEST_BUCKET_NAME)
            for obj in bkt.objects():
                bkt.delete_object(obj.name)
            bkt.delete()

        bucket = storage.ensure_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        assert storage.bucket_exists(TEST_BUCKET_NAME)

    @pytest.mark.order(2)
    def test_ensure_bucket_idempotent(self, storage: MinioStorage):
        """ensure_bucket 对已存在的 Bucket 应幂等返回。"""
        bucket1 = storage.ensure_bucket(TEST_BUCKET_NAME)
        bucket2 = storage.ensure_bucket(TEST_BUCKET_NAME)
        assert bucket1 is not None
        assert bucket2 is not None
        assert bucket1.name == bucket2.name


# ==================== Read ====================

class TestBucketRead:
    """Bucket 读取相关测试。"""

    @pytest.mark.order(3)
    def test_bucket_exists(self, storage: MinioStorage):
        """bucket_exists 对已存在的 Bucket 应返回 True。"""
        assert storage.bucket_exists(TEST_BUCKET_NAME) is True

    @pytest.mark.order(4)
    def test_bucket_not_exists(self, storage: MinioStorage):
        """bucket_exists 对不存在的 Bucket 应返回 False。"""
        assert storage.bucket_exists("non-existent-bucket-xyz-99999") is False

    @pytest.mark.order(5)
    def test_get_bucket(self, storage: MinioStorage):
        """get_bucket 应返回正确的 MinioBucket 实例。"""
        bucket = storage.get_bucket(TEST_BUCKET_NAME)
        assert bucket is not None
        assert isinstance(bucket, MinioBucket)
        assert bucket.name == TEST_BUCKET_NAME

    @pytest.mark.order(6)
    def test_get_bucket_not_found(self, storage: MinioStorage):
        """get_bucket 对不存在的 Bucket 应返回 None。"""
        bucket = storage.get_bucket("non-existent-bucket-xyz-99999")
        assert bucket is None

    @pytest.mark.order(7)
    def test_list_buckets(self, storage: MinioStorage):
        """buckets 方法应返回包含测试 Bucket 的列表。"""
        buckets = storage.buckets()
        assert isinstance(buckets, list)
        assert any(b.name == TEST_BUCKET_NAME for b in buckets)


# ==================== Update (对象操作) ====================

class TestBucketObjectOperations:
    """Bucket 内对象的 CRUD 操作测试。"""

    @pytest.mark.order(8)
    def test_fput_and_fget(self, bucket: MinioBucket):
        """fput 上传文件后，fget 应能下载到相同内容。"""
        object_key = "test-crud/fput_fget.txt"
        content = "hello any-storage minio bucket crud test"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            upload_path = f.name

        try:
            bucket.fput(upload_path, object_key)

            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                download_path = f.name

            bucket.fget(object_key, download_path)

            with open(download_path, "r") as f:
                assert f.read() == content
        finally:
            os.unlink(upload_path)
            if os.path.exists(download_path):
                os.unlink(download_path)
            bucket.delete_object(object_key)

    @pytest.mark.order(9)
    def test_objects_list(self, bucket: MinioBucket):
        """objects 应返回已上传的对象列表。"""
        object_key = "test-crud/list_obj.txt"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("list test")
            upload_path = f.name

        try:
            bucket.fput(upload_path, object_key)
            objs = bucket.objects(prefix="test-crud/")
            keys = [o.name for o in objs]
            assert object_key in keys
        finally:
            os.unlink(upload_path)
            bucket.delete_object(object_key)

    @pytest.mark.order(10)
    def test_get_object(self, bucket: MinioBucket):
        """get_object 应返回正确的 MinioObject 实例。"""
        object_key = "test-crud/get_obj.txt"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("get test")
            upload_path = f.name

        try:
            bucket.fput(upload_path, object_key)
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert isinstance(obj, MinioObject)
            assert obj.name == object_key
        finally:
            os.unlink(upload_path)
            bucket.delete_object(object_key)

    @pytest.mark.order(11)
    def test_object_exists_and_size(self, bucket: MinioBucket):
        """已上传的对象应存在且 size 大于 0。"""
        object_key = "test-crud/exists_size.txt"
        content = "size test content"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            upload_path = f.name

        try:
            bucket.fput(upload_path, object_key)
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.exists() is True
            assert obj.size > 0
        finally:
            os.unlink(upload_path)
            bucket.delete_object(object_key)

    @pytest.mark.order(12)
    def test_put_and_get(self, bucket: MinioBucket):
        """put 上传字节数据后，get 应能读取到相同内容。"""
        object_key = "test-crud/put_get.txt"
        content = "hello any-storage minio put/get test"
        data = content.encode("utf-8")

        try:
            bucket.put(data, object_key, content_type="text/plain")

            result = bucket.get(object_key)
            assert isinstance(result, bytes)
            assert result == data
            assert result.decode("utf-8") == content
        finally:
            bucket.delete_object(object_key)

    @pytest.mark.order(13)
    def test_presigned_get_url(self, bucket: MinioBucket):
        """presigned_get_url 应返回可通过 GET 下载对象的 URL。"""
        object_key = "test-crud/presigned_get.txt"
        content = "presigned get test"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            upload_path = f.name

        try:
            bucket.fput(upload_path, object_key)
            url = bucket.presigned_get_url(object_key)
            assert isinstance(url, str)
            assert len(url) > 0
            # 通过 HTTP GET 验证 URL 可用
            response = requests.get(url)
            assert response.status_code == 200
            assert response.text == content
        finally:
            os.unlink(upload_path)
            bucket.delete_object(object_key)

    @pytest.mark.order(14)
    def test_presigned_put_url(self, bucket: MinioBucket):
        """presigned_put_url 应返回可通过 PUT 上传对象的 URL。"""
        object_key = "test-crud/presigned_put.txt"
        content = "presigned put test"

        try:
            url = bucket.presigned_put_url(object_key)
            assert isinstance(url, str)
            assert len(url) > 0
            # 通过 HTTP PUT 验证 URL 可用
            response = requests.put(url, data=content.encode("utf-8"))
            assert response.status_code == 200
            # 验证上传成功
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.exists() is True
        finally:
            bucket.delete_object(object_key)


# ==================== Delete ====================

class TestBucketDelete:
    """Bucket 删除相关测试。"""

    @pytest.mark.order(15)
    def test_delete_object(self, bucket: MinioBucket):
        """delete_object 后对象应不再存在。"""
        object_key = "test-crud/delete_obj.txt"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("to be deleted")
            upload_path = f.name

        try:
            bucket.fput(upload_path, object_key)
            obj = bucket.get_object(object_key)
            assert obj is not None

            bucket.delete_object(object_key)
            # 删除后对象应不存在
            assert obj.exists() is False
        finally:
            os.unlink(upload_path)

    @pytest.mark.order(16)
    def test_delete_bucket(self, storage: MinioStorage):
        """delete 后 Bucket 应不再存在。"""
        del_name = f"{TEST_BUCKET_NAME}"

        bucket = storage.ensure_bucket(del_name)
        assert bucket is not None
        assert storage.bucket_exists(del_name)

        bucket.delete()
        assert storage.bucket_exists(del_name) is False
