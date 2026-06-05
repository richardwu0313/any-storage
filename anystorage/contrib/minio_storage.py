from minio import Minio, S3Error
import urllib3
from datetime import timedelta
import os
import certifi
from typing import List
from typing import Optional
from loguru import logger

from anystorage.base import BaseStorage
from anystorage.base import BaseBucket
from anystorage.base import BaseObject
from anystorage.settings import MINIO_STORAGE_CONFIG


class MinioStorage(BaseStorage):
    """MinIO 存储客户端封装类。

    继承自 BaseStorage，提供与 MinIO 服务交互的底层实现，
    包括 Bucket 的列举、创建、获取和存在性检查等功能。

    Attributes:
        endpoint (str): MinIO 服务的 Endpoint。
        access_key_id (str): MinIO Access Key ID。
        access_key_secret (str): MinIO Secret Access Key。
        use_ssl (bool): 是否使用 SSL 连接。
        _minio_storage (Minio): 底层 MinIO 客户端实例。
    """

    def __init__(self, 
                 endpoint: str=MINIO_STORAGE_CONFIG["endpoint"],
                 access_key_id: str=MINIO_STORAGE_CONFIG["access_key_id"],
                 access_key_secret: str=MINIO_STORAGE_CONFIG["access_key_secret"],
                 connect_timeout: int = MINIO_STORAGE_CONFIG["connect_timeout"],
                 read_timeout: int = MINIO_STORAGE_CONFIG["read_timeout"],
                 use_ssl: bool = MINIO_STORAGE_CONFIG["use_ssl"],):
        """初始化 MinIO 存储实例。

        Args:
            endpoint (str, optional): MinIO 服务的 Endpoint。默认从配置中读取。
            access_key_id (str, optional): MinIO Access Key ID。默认从配置中读取。
            access_key_secret (str, optional): MinIO Secret Access Key。默认从配置中读取。
            use_ssl (bool, optional): 是否使用 SSL 连接。默认从配置中读取。
        """
        super().__init__(endpoint, access_key_id, access_key_secret, use_ssl)
        self.connect_timeout = timedelta(seconds=connect_timeout).seconds
        self.read_timeout = timedelta(seconds=read_timeout).seconds
        self._minio_storage = Minio(endpoint=endpoint,
                                    access_key=access_key_id,
                                    secret_key=access_key_secret,
                                    secure=use_ssl,
                                    http_client=urllib3.PoolManager(
                                        timeout=urllib3.util.Timeout(connect=self.connect_timeout,
                                                                     read=self.read_timeout),
                                        maxsize=120,
                                        cert_reqs="CERT_REQUIRED",
                                        ca_certs=os.environ.get("SSL_CERT_FILE") or certifi.where(),
                                        retries=urllib3.Retry(
                                            total=5,
                                            backoff_factor=0.2,
                                            status_forcelist=[500, 502, 503, 504],
                                        ),
                                    ))

    def bucket_exists(self, name: str) -> bool:
        """判断指定名称的 Bucket 是否存在。

        Args:
            name (str): 需要检查的 Bucket 名称。

        Returns:
            bool: 如果 Bucket 存在返回 True，否则返回 False。
        """
        return self._minio_storage.bucket_exists(name)

    def get_bucket(self, name: str) -> Optional["MinioBucket"]:
        """根据名称获取指定的 MinIO Bucket 实例。

        Args:
            name (str): 需要获取的 Bucket 名称。

        Returns:
            Optional[MinioBucket]: 如果 Bucket 存在则返回其实例，否则返回 None。
        """
        if self.bucket_exists(name):
            return MinioBucket(name=name, storage=self)
        return None

    def buckets(self) -> List["MinioBucket"]:
        """获取当前账号下所有的 MinIO Bucket 列表。

        Returns:
            List[MinioBucket]: 包含所有 Bucket 实例的列表。
        """
        buckets = self._minio_storage.list_buckets()
        bucket_objs = []
        for bucket in buckets:
            bucket_objs.append(MinioBucket(name=bucket.name, storage=self))
        return bucket_objs

    def ensure_bucket(self, name: str) -> Optional["MinioBucket"]:
        """确保指定名称的 Bucket 存在，若不存在则创建。

        Args:
            name (str): 需要确保存在的 Bucket 名称。

        Returns:
            Optional[MinioBucket]: 创建或已存在的 Bucket 实例。
        """
        if not self.bucket_exists(name):
            self._minio_storage.make_bucket(name)
        return self.get_bucket(name)


class MinioBucket(BaseBucket):
    """MinIO Bucket 封装类。

    继承自 BaseBucket，提供对特定 MinIO Bucket 的操作，
    包括文件的上传、下载、对象管理及 Bucket 自身的删除等。

    Attributes:
        _minio_storage (Minio): 底层 MinIO 客户端实例。
        _minio_bucket: MinIO Bucket 引用（当前未使用）。
    """

    def __init__(self, name, storage: MinioStorage):
        """初始化 MinioBucket 实例。

        Args:
            name (str): Bucket 的名称。
            storage (MinioStorage): 关联的 MinioStorage 存储客户端实例。
        """
        super().__init__(name, storage)
        endpoint = self.storage.endpoint
        access_key_id = self.storage.access_key_id
        access_key_secret = self.storage.access_key_secret
        use_ssl = self.storage.use_ssl
        connect_timeout = self.storage.connect_timeout
        read_timeout = self.storage.read_timeout
        self._minio_storage = Minio(endpoint=endpoint,
                                    access_key=access_key_id,
                                    secret_key=access_key_secret,
                                    secure=use_ssl,
                                    http_client=urllib3.PoolManager(
                                        timeout=urllib3.util.Timeout(connect=connect_timeout,
                                                                     read=read_timeout),
                                        maxsize=120,
                                        cert_reqs="CERT_REQUIRED",
                                        ca_certs=os.environ.get("SSL_CERT_FILE") or certifi.where(),
                                        retries=urllib3.Retry(
                                            total=5,
                                            backoff_factor=0.2,
                                            status_forcelist=[500, 502, 503, 504],
                                        ),
                                    ))
        self._minio_bucket = None

    def fput(self, local_path: str, object_key: str) -> None:
        """将本地文件上传至对象存储。

        Args:
            local_path (str): 本地文件的路径。
            object_key (str): 对象存储中的目标对象键（Object Key）。
        """
        self._minio_storage.fput_object(bucket_name=self.name,
                                        file_path=local_path,
                                        object_name=object_key)

    def fget(self, object_key: str, local_path: str) -> None:
        """从对象存储下载文件到本地。

        Args:
            object_key (str): 对象存储中的对象键（Object Key）。
            local_path (str): 本地保存的目标文件路径。
        """
        self._minio_storage.fget_object(bucket_name=self.name,
                                        file_path=local_path,
                                        object_name=object_key)

    def objects(self, prefix: str = "") -> List["MinioObject"]:
        """列举 Bucket 中匹配指定前缀的所有对象。

        Args:
            prefix (str, optional): 对象键的前缀过滤条件。默认为空字符串，即列举所有对象。

        Returns:
            List[MinioObject]: 包含所有匹配对象的 MinioObject 实例列表。
        """
        objs = self._minio_storage.list_objects(bucket_name=self.name, prefix=prefix)
        return [MinioObject(name=obj.object_name, bucket=self, storage=self.storage) for obj in objs]

    def delete(self) -> None:
        """删除当前 Bucket。

        如果 Bucket 不存在则仅记录警告日志，不执行删除操作。
        """
        if self.storage.bucket_exists(self.name):
            self._minio_storage.remove_bucket(self.name)
            logger.info(f"Minio Bucket {self.name} deleted")
        else:
            logger.warning(f"Minio Bucket {self.name} not exist, no need to delete")

    def delete_object(self, object_key: str) -> None:
        """删除指定对象。

        Args:
            object_key (str): 需要删除的对象键（Object Key）。
        """
        self._minio_storage.remove_object(self.name, object_key)

    def get_object(self, object_key: str) -> Optional["MinioObject"]:
        """获取指定对象。

        Args:
            object_key (str): 需要获取的对象键（Object Key）。

        Returns:
            Optional[MinioObject]: 如果对象存在则返回其实例，否则返回 None。
        """
        if self._minio_storage.get_object(bucket_name=self.name, object_name=object_key):
            return MinioObject(name=object_key, bucket=self, storage=self.storage)
        return None

    def presigned_get_url(self, object_key: str, expires: int = 3600) -> str:
        """生成用于下载对象的预签名 URL。

        Args:
            object_key (str): 对象存储中的对象键（Object Key）。
            expires (int, optional): 预签名 URL 的过期时间（秒）。默认为 3600 秒。

        Returns:
            str: 预签名下载 URL。
        """
        return self._minio_storage.presigned_get_object(bucket_name=self.name,
                                                        object_name=object_key,
                                                        expires=timedelta(seconds=expires))

    def presigned_put_url(self, object_key: str, expires: int = 3600) -> str:
        """生成用于上传对象的预签名 URL。

        Args:
            object_key (str): 对象存储中的目标对象键（Object Key）。
            expires (int, optional): 预签名 URL 的过期时间（秒）。默认为 3600 秒。

        Returns:
            str: 预签名上传 URL。
        """
        return self._minio_storage.presigned_put_object(bucket_name=self.name,
                                                        object_name=object_key,
                                                        expires=timedelta(seconds=expires))


class MinioObject(BaseObject):
    """MinIO Object 封装类。

    继承自 BaseObject，提供对特定 MinIO 对象的操作，
    包括对象的存在性检查及大小获取等。

    Attributes:
        _minio_storage (Minio): 底层 MinIO 客户端实例。
    """

    def __init__(self, name: str, bucket: MinioBucket, storage: MinioStorage):
        """初始化 MinioObject 实例。

        Args:
            name (str): 对象的名称（Object Key）。
            bucket (MinioBucket): 对象所属的 MinioBucket 实例。
            storage (MinioStorage): 关联的 MinioStorage 存储客户端实例。
        """
        super().__init__(name, bucket, storage)
        endpoint = self.storage.endpoint
        access_key_id = self.storage.access_key_id
        access_key_secret = self.storage.access_key_secret
        use_ssl = self.storage.use_ssl
        connect_timeout = self.storage.connect_timeout
        read_timeout = self.storage.read_timeout
        self._minio_storage = Minio(endpoint=endpoint,
                                    access_key=access_key_id,
                                    secret_key=access_key_secret,
                                    secure=use_ssl,
                                    http_client=urllib3.PoolManager(
                                        timeout=urllib3.util.Timeout(connect=connect_timeout,
                                                                     read=read_timeout),
                                        maxsize=120,
                                        cert_reqs="CERT_REQUIRED",
                                        ca_certs=os.environ.get("SSL_CERT_FILE") or certifi.where(),
                                        retries=urllib3.Retry(
                                            total=5,
                                            backoff_factor=0.2,
                                            status_forcelist=[500, 502, 503, 504],
                                        ),
                                    ))

    def exists(self) -> bool:
        """检查当前对象是否存在于 MinIO 中。

        Returns:
            bool: 如果对象存在返回 True，否则返回 False。
        """
        try:
            self._minio_storage.stat_object(bucket_name=self.bucket_name, object_name=self.name)
        except S3Error as ex:
            return False
        return True

    @property
    def size(self) -> int:
        """获取当前对象的大小（字节数）。

        Returns:
            int: 对象的大小（字节数）。如果对象不存在则返回 -1。
        """
        if self.exists():
            return self._minio_storage.stat_object(self.bucket_name, self.name).size
        return -1