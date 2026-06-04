import os
import tempfile
import time

import pytest
from dotenv import load_dotenv
from pathlib import Path

from anystorage.contrib.minio_storage import MinioStorage
from anystorage.contrib.minio_storage import MinioBucket
from anystorage.contrib.minio_storage import MinioObject


# 测试用的 Bucket 名称，避免与生产环境冲突
TEST_BUCKET_NAME = "test-obj-" + str(int(time.time()))

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


@pytest.fixture(scope="module")
def bucket(storage: MinioStorage) -> MinioBucket:
    """确保测试 Bucket 存在并返回实例，模块级别共享。

    测试结束后自动清理：删除 Bucket 中所有对象后删除 Bucket 本身。
    """
    bucket = storage.ensure_bucket(TEST_BUCKET_NAME)
    assert bucket is not None, f"创建测试 Bucket {TEST_BUCKET_NAME} 失败"
    yield bucket
    # teardown: 清理 Bucket 中所有对象后删除 Bucket
    for obj in bucket.objects():
        bucket.delete_object(obj.name)
    bucket.delete()


def _upload_temp_file(bucket: MinioBucket, object_key: str, content: str) -> str:
    """辅助函数：创建临时文件并上传到 MinIO，返回本地临时文件路径。"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        upload_path = f.name
    bucket.fput(upload_path, object_key)
    return upload_path


# ==================== Read ====================

class TestObjectRead:
    """MinioObject 读取相关测试。"""

    @pytest.mark.order(1)
    def test_object_name(self, bucket: MinioBucket):
        """MinioObject 的 name 属性应等于 object_key。"""
        object_key = "test-obj/name.txt"
        try:
            _upload_temp_file(bucket, object_key, "name test")
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.name == object_key
        finally:
            bucket.delete_object(object_key)

    @pytest.mark.order(2)
    def test_object_bucket_name(self, bucket: MinioBucket):
        """MinioObject 的 bucket_name 属性应返回所属 Bucket 名称。"""
        object_key = "test-obj/bucket_name.txt"
        try:
            _upload_temp_file(bucket, object_key, "bucket name test")
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.bucket_name == TEST_BUCKET_NAME
        finally:
            bucket.delete_object(object_key)

    @pytest.mark.order(3)
    def test_object_exists_true(self, bucket: MinioBucket):
        """exists 对已存在的对象应返回 True。"""
        object_key = "test-obj/exists_true.txt"
        try:
            _upload_temp_file(bucket, object_key, "exists test")
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.exists() is True
        finally:
            bucket.delete_object(object_key)

    @pytest.mark.order(4)
    def test_object_exists_false(self, bucket: MinioBucket):
        """exists 对不存在的对象应返回 False。"""
        # 手动构造一个不存在的 MinioObject（绕过 get_object 检查）
        obj = MinioObject(name="non-existent-key-99999",
                          bucket=bucket,
                          storage=bucket.storage)
        assert obj.exists() is False

    @pytest.mark.order(5)
    def test_object_size(self, bucket: MinioBucket):
        """size 应返回正确的对象字节数。"""
        object_key = "test-obj/size.txt"
        content = "hello size test"
        try:
            _upload_temp_file(bucket, object_key, content)
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.size == len(content.encode("utf-8"))
        finally:
            bucket.delete_object(object_key)

    @pytest.mark.order(6)
    def test_object_size_not_exist(self, bucket: MinioBucket):
        """不存在的对象 size 应返回 -1。"""
        obj = MinioObject(name="non-existent-key-99999",
                          bucket=bucket,
                          storage=bucket.storage)
        assert obj.size == -1


# ==================== Update (通过 Bucket 操作) ====================

class TestObjectUpdate:
    """MinioObject 更新相关测试（通过 Bucket 的 fput/fget 间接验证）。"""

    @pytest.mark.order(7)
    def test_overwrite_object(self, bucket: MinioBucket):
        """对同一 object_key 再次 fput 应覆盖原内容。"""
        object_key = "test-obj/overwrite.txt"
        try:
            _upload_temp_file(bucket, object_key, "old content")
            obj = bucket.get_object(object_key)
            assert obj is not None
            old_size = obj.size

            # 覆盖上传
            _upload_temp_file(bucket, object_key, "new content with more data")
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.size > old_size
        finally:
            bucket.delete_object(object_key)

    @pytest.mark.order(8)
    def test_download_content_matches(self, bucket: MinioBucket):
        """fget 下载的内容应与上传内容一致。"""
        object_key = "test-obj/download.txt"
        content = "download content test 中文"
        upload_path = ""
        download_path = ""
        try:
            upload_path = _upload_temp_file(bucket, object_key, content)

            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                download_path = f.name

            bucket.fget(object_key, download_path)

            with open(download_path, "r") as f:
                assert f.read() == content
        finally:
            if upload_path and os.path.exists(upload_path):
                os.unlink(upload_path)
            if download_path and os.path.exists(download_path):
                os.unlink(download_path)
            bucket.delete_object(object_key)


# ==================== Delete ====================

class TestObjectDelete:
    """MinioObject 删除相关测试。"""

    @pytest.mark.order(9)
    def test_delete_existing_object(self, bucket: MinioBucket):
        """删除已存在的对象后，exists 应返回 False。"""
        object_key = "test-obj/delete.txt"
        try:
            _upload_temp_file(bucket, object_key, "to be deleted")
            obj = bucket.get_object(object_key)
            assert obj is not None
            assert obj.exists() is True

            bucket.delete_object(object_key)

            # 构造 MinioObject 检查 exists
            check_obj = MinioObject(name=object_key,
                                    bucket=bucket,
                                    storage=bucket.storage)
            assert check_obj.exists() is False
        finally:
            try:
                bucket.delete_object(object_key)
            except Exception:
                pass

    @pytest.mark.order(10)
    def test_objects_list_after_delete(self, bucket: MinioBucket):
        """删除对象后，objects 列表中不应再包含该对象。"""
        object_key = "test-obj/list_after_delete.txt"
        try:
            _upload_temp_file(bucket, object_key, "list delete test")
            objs = bucket.objects(prefix="test-obj/list_after_delete")
            assert any(o.name == object_key for o in objs)

            bucket.delete_object(object_key)
            objs = bucket.objects(prefix="test-obj/list_after_delete")
            assert not any(o.name == object_key for o in objs)
        finally:
            try:
                bucket.delete_object(object_key)
            except Exception:
                pass
