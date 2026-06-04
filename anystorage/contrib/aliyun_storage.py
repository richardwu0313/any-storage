import oss2
import os
from typing import List
from typing import Optional
from loguru import logger

from oss2.exceptions import OssError

from anystorage.base import BaseStorage
from anystorage.base import BaseObject
from anystorage.base import BaseBucket
from anystorage.settings import ALIYUN_STORAGE_CONFIG


class AliyunStorage(BaseStorage):
    """Aliyun OSS 存储客户端封装类。

    继承自 BaseStorage，提供与Aliyun OSS 交互的底层实现，
    包括 Bucket 的列举、创建、获取和存在性检查等功能。

    Attributes:
        endpoint (str): Aliyun OSS 服务的 Endpoint。
        access_key_id (str): Aliyun AccessKey ID。
        access_key_secret (str): Aliyun AccessKey Secret。
        use_ssl (bool): 是否使用 SSL 连接。
        region (str): Aliyun OSS 区域。
        delimiter (str): 对象键的分隔符，默认为 "/"。
        auth (oss2.Auth): Aliyun OSS 认证实例。
        service (oss2.Service): Aliyun OSS 服务实例。
    """

    def __init__(self,
                 endpoint: str=ALIYUN_STORAGE_CONFIG["endpoint"],
                 access_key_id: str=ALIYUN_STORAGE_CONFIG["access_key_id"],
                 access_key_secret: str=ALIYUN_STORAGE_CONFIG["access_key_secret"],
                 region: str=ALIYUN_STORAGE_CONFIG["region"],
                 connect_timeout: int=ALIYUN_STORAGE_CONFIG["connect_timeout"],
                 use_ssl: bool=ALIYUN_STORAGE_CONFIG["use_ssl"]):
        """初始化阿里云 OSS 存储实例。

        Args:
            endpoint (str, optional): Aliyun OSS 服务的 Endpoint。默认从配置中读取。
            access_key_id (str, optional): Aliyun AccessKey ID。默认从配置中读取。
            access_key_secret (str, optional): Aliyun AccessKey Secret。默认从配置中读取。
            region (str, optional): Aliyun OSS 区域。默认从配置中读取。
            connect_timeout (int, optional): 连接超时时间（秒）。默认从配置中读取。
            use_ssl (bool, optional): 是否使用 SSL 连接。默认从配置中读取。

        Raises:
            ValueError: 当 endpoint、access_key_id 或 access_key_secret 配置缺失时抛出。
        """
        if not all([endpoint, access_key_id, access_key_secret]):
            raise ValueError("Aliyun OSS settings环境变量配置错误")
        # endpoint 如果没有 http|https:// 开头，则根据 use_ssl 补全 endpoint 协议前缀
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"{'https' if use_ssl else 'http'}://{endpoint}"
        super().__init__(endpoint, access_key_id, access_key_secret, use_ssl)
        self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.region = region
        self.delimiter = "/"
        self.service = oss2.Service(auth=self.auth,
                                    endpoint=self.endpoint,
                                    connect_timeout=connect_timeout,
                                    region=region)

    @property
    def buckets(self) -> List["AliyunBucket"]:
        """获取当前账号下所有的 Aliyun OSS Bucket 列表。

        Returns:
            List[AliyunBucket]: 包含所有 Bucket 实例的列表。
        """
        buckets = []
        for bucket in oss2.BucketIterator(self.service):
            bucket_obj = AliyunBucket(name=bucket.name,
                                      storage=self)
            buckets.append(bucket_obj)
        return buckets

    def ensure_bucket(self, name: str) -> Optional["AliyunBucket"]:
        """确保指定名称的 Aliyun OSS Bucket 存在，若不存在则创建。

        创建的 Aliyun OSS Bucket 默认为私有读写权限（PRIVATE）和标准存储类型（STANDARD）。

        Args:
            name (str): 需要确保存在的 Aliyun OSS Bucket 名称。

        Raises:
            OssError: 当创建 Aliyun OSS Bucket 失败或发生其他 Aliyun OSS 相关错误时抛出。
        """
        try:
            bucket_obj = self.get_bucket(name)
            if not bucket_obj:
                bkt = oss2.Bucket(self.auth, self.endpoint, name)
                bkt.create_bucket(permission=oss2.BUCKET_ACL_PRIVATE,
                                  input=oss2.models.BucketCreateConfig(oss2.BUCKET_STORAGE_CLASS_STANDARD))
                logger.info(f"Aliyun OSS Bucket {name} 创建成功")
                bucket_obj = self.get_bucket(name)
            return bucket_obj
        except OssError as e:
            logger.error(f"Aliyun OSS Bucket 初始化失败: {e}")
        return None

    def get_bucket(self, name: str) -> Optional["AliyunBucket"]:
        """根据名称获取指定的 Aliyun OSS Bucket 实例。

        Args:
            name (str): 需要获取的 Aliyun OSS Bucket 名称。

        Returns:
            Optional[AliyunBucket]: 如果找到匹配的 Aliyun OSS Bucket 则返回其实例，否则返回 None。
        """
        for bucket in oss2.BucketIterator(self.service):
            if bucket.name == name:
                return AliyunBucket(name=bucket.name, storage=self)
        return None

    def bucket_exists(self, name: str) -> bool:
        """判断指定名称的 Bucket 是否存在。

        Args:
            name (str): 需要检查的 Aliyun OSS Bucket 名称。

        Returns:
            bool: 如果 Aliyun OSS Bucket 存在返回 True，否则返回 False。
        """
        if not self.get_bucket(name):
            return False
        return True


class AliyunBucket(BaseBucket):
    """Aliyun OSS Bucket 封装类。

    继承自 BaseBucket，提供对特定 Aliyun OSS Bucket 的操作，
    包括文件的上传、下载、对象管理及 Bucket 自身的删除等。

    Attributes:
        _aliyun_bucket (oss2.Bucket): 底层的 Aliyun OSS Bucket 实例。
    """

    def __init__(self, name: str, storage: AliyunStorage):
        """初始化 AliyunBucket 实例。

        Args:
            name (str): Bucket 的名称。
            storage (AliyunStorage): 关联的 AliyunStorage 存储客户端实例。
        """
        super().__init__(name, storage)
        self._aliyun_bucket = oss2.Bucket(auth=self.storage.auth,
                                          endpoint=self.storage.endpoint,
                                          bucket_name=name)

    def fput(self, local_path: str, object_key: str) -> None:
        """将本地文件上传至对象存储。

        Args:
            local_path (str): 本地文件的路径。
            object_key (str): 对象存储中的目标对象键（Object Key）。

        Raises:
            FileNotFoundError: 当本地文件不存在时抛出。
            AssertionError: 当底层的阿里云 OSS Bucket 实例不存在时抛出。
        """
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Aliyun OSS 本地文件不存在: {local_path}")
        assert self._aliyun_bucket, "Aliyun OSS Bucket 不存在"
        self._aliyun_bucket.put_object_from_file(object_key, local_path)
        logger.info(f"Aliyun OSS 上传: {local_path} → {object_key}")

    def fget(self, object_key: str, local_path: str) -> None:
        """从对象存储下载文件到本地。

        Args:
            object_key (str): 对象存储中的对象键（Object Key）。
            local_path (str): 本地保存的目标文件路径。

        Raises:
            AssertionError: 当底层的阿里云 OSS Bucket 实例不存在时抛出。
        """
        assert self._aliyun_bucket, "Aliyun OSS Bucket 不存在"
        self._aliyun_bucket.get_object_to_file(object_key, local_path)
        logger.info(f"Aliyun OSS 下载: {object_key} → {local_path}")

    def delete(self) -> None:
        """删除当前 Bucket。

        Raises:
            AssertionError: 当底层的阿里云 OSS Bucket 实例不存在时抛出。
        """
        assert self._aliyun_bucket, f"Aliyun OSS Bucket {self.name}不存在"
        for bkt in oss2.BucketIterator(self.storage.service):
            if bkt.name == self.name:
                self._aliyun_bucket.delete_bucket()
        logger.info(f"Aliyun OSS 删除 bucket: {self.name}")

    def delete_object(self, object_key):
        """删除指定对象。

        Args:
            object_key (str): 需要删除的对象键（Object Key）。

        Raises:
            AssertionError: 当底层的阿里云 OSS Bucket 实例不存在时抛出。
        """
        assert self._aliyun_bucket, "Aliyun OSS Bucket 不存在"
        self._aliyun_bucket.delete_object(object_key)
        logger.info(f"Aliyun OSS 删除 object: {object_key}")

    def get_object(self, object_key: str) -> Optional["AliyunObject"]:
        """获取指定对象键的 AliyunObject 实例。

        Args:
            object_key (str): 需要获取的对象键（Object Key）。

        Returns:
            Optional[AliyunObject]: 对应的阿里云 OSS 对象实例。

        Raises:
            AssertionError: 当底层的阿里云 OSS Bucket 实例不存在时抛出。
        """
        assert self._aliyun_bucket, "Aliyun OSS Bucket 不存在"
        if self._aliyun_bucket.object_exists(object_key):
            obj = AliyunObject(object_key=object_key,
                               bucket=self,
                               storage=self.storage)
            return obj
        return None

    def objects(self, prefix: str = "") -> List["AliyunObject"]:
        """列举 Bucket 中匹配指定前缀的所有对象。

        Args:
            prefix (str, optional): 对象键的前缀过滤条件。默认为空字符串，即列举所有对象。

        Returns:
            List[AliyunObject]: 包含所有匹配对象的 AliyunObject 实例列表。

        Raises:
            AssertionError: 当底层的阿里云 OSS Bucket 实例不存在时抛出。
        """
        assert self._aliyun_bucket, "Aliyun OSS Bucket 不存在"
        obj_list = []
        for obj in oss2.ObjectIterator(bucket=self._aliyun_bucket,
                                       prefix=prefix):
            obj_list.append(AliyunObject(object_key=obj.key,
                                         bucket=self,
                                         storage=self.storage))
        return obj_list


class AliyunObject(BaseObject):
    """Aliyun OSS Object 封装类。

    继承自 BaseObject，提供对特定 Aliyun OSS 对象的操作，
    包括对象的删除、大小获取及存在性检查等。

    Attributes:
        _aliyun_bucket (oss2.Bucket): 对象所属的底层 Aliyun OSS Bucket 实例。
    """

    def __init__(self, object_key: str, bucket: "AliyunBucket", storage: "AliyunStorage"):
        """初始化 AliyunObject 实例。

        Args:
            object_key (str): 对象的名称（Object Key）。
            bucket (AliyunBucket): 对象所属的 AliyunBucket 实例。
            storage (AliyunStorage): 关联的 AliyunStorage 存储客户端实例。
        """
        super().__init__(object_key, bucket, storage)
        self._aliyun_bucket = oss2.Bucket(auth=self.storage.auth,
                                          endpoint=self.storage.endpoint,
                                          bucket_name=self.bucket.name)

    @property
    def size(self) -> int:
        """获取当前对象的大小（字节数）。

        Returns:
            int: 对象的大小。如果获取失败则返回 0。
        """
        headers = self._aliyun_bucket.head_object(self.name).headers
        return int(headers.get("Content-Length", 0))

    def exists(self) -> bool:
        """检查当前对象是否存在于 OSS 中。

        Returns:
            bool: 如果对象存在返回 True，否则返回 False。
        """
        return self._aliyun_bucket.object_exists(self.name)