from abc import ABC, abstractmethod
from typing import List


class BaseStorage(ABC):
    """统一存储抽象接口"""
    def __init__(self,
                 endpoint: str,
                 access_key_id: str,
                 access_key_secret: str,
                 use_ssl: bool):
        self.endpoint = endpoint
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.use_ssl = use_ssl

    @abstractmethod
    def bucket_exists(self, name: str) -> bool:
        """判断 Bucket 是否存在"""
        pass

    @abstractmethod
    def get_bucket(self, name: str) -> "BaseBucket":
        """获取存储桶实例"""
        pass

    @abstractmethod
    def buckets(self) -> List["BaseBucket"]:
        """列出所有存储桶名称"""
        pass

    @abstractmethod
    def ensure_bucket(self, name: str) -> "BaseBucket":
        """确保存储桶存在，不存在则创建"""
        pass


class BaseBucket(ABC):
    """统一存储桶抽象接口"""

    def __init__(self, name, storage: BaseStorage):
        assert storage is not None, "storage不能为空"
        self.name = name
        self.storage = storage

    @abstractmethod
    def fput(self, local_path: str, object_key: str) -> None:
        """本地上传至对象存储"""
        pass

    @abstractmethod
    def fget(self, object_key: str, local_path: str) -> None:
        """对象存储下载到本地"""
        pass

    @abstractmethod
    def presigned_get_url(self, object_key: str, expires: int = 3600):
        """获取预签名 URL"""
        pass

    @abstractmethod
    def presigned_put_url(self, object_key: str, expires: int = 3600):
        """获取预签名 URL"""
        pass

    @abstractmethod
    def objects(self, prefix: str = "") -> List["BaseObject"]:
        """列出指定前缀下所有对象 key"""
        pass

    @abstractmethod
    def delete(self) -> None:
        """删除存储桶"""
        pass

    @abstractmethod
    def delete_object(self, object_key: str) -> None:
        """删除对象"""
        pass


class BaseObject(ABC):
    """统一对象抽象接口"""

    def __init__(self, object_key: str, bucket: BaseBucket, storage: BaseStorage):
        self.name = object_key
        self.bucket = bucket
        self.storage = storage

    @property
    def bucket_name(self) -> str:
        return self.bucket.name

    @abstractmethod
    def exists(self) -> bool:
        """判断对象是否存在"""
        pass

    @abstractmethod
    def size(self) -> int:
        """获取对象大小（字节）"""
        pass