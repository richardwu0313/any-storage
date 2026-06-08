import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import List
from typing import Optional
from loguru import logger

from anystorage.base import BaseStorage
from anystorage.base import BaseBucket
from anystorage.base import BaseObject
from anystorage.settings import RUSTFS_STORAGE_CONFIG


class RustfsStorage(BaseStorage):
    """RustFS 存储客户端封装类。

    继承自 BaseStorage，通过 boto3 SDK 提供与 RustFS 服务交互的底层实现，
    包括 Bucket 的列举、创建、获取和存在性检查等功能。
    RustFS 兼容 S3 API，因此使用 boto3 作为客户端。

    Attributes:
        endpoint (str): RustFS 服务的 Endpoint。
        access_key_id (str): RustFS Access Key ID。
        access_key_secret (str): RustFS Secret Access Key。
        use_ssl (bool): 是否使用 SSL 连接。
        _s3_client (boto3.client): 底层 boto3 S3 客户端实例。
    """

    def __init__(self,
                 endpoint: str = RUSTFS_STORAGE_CONFIG["endpoint"],
                 access_key_id: str = RUSTFS_STORAGE_CONFIG["access_key_id"],
                 access_key_secret: str = RUSTFS_STORAGE_CONFIG["access_key_secret"],
                 use_ssl: bool = RUSTFS_STORAGE_CONFIG["use_ssl"]):
        """初始化 RustFS 存储实例。

        Args:
            endpoint (str, optional): RustFS 服务的 Endpoint。默认从配置中读取。
            access_key_id (str, optional): RustFS Access Key ID。默认从配置中读取。
            access_key_secret (str, optional): RustFS Secret Access Key。默认从配置中读取。
            use_ssl (bool, optional): 是否使用 SSL 连接。默认从配置中读取。

        Raises:
            ValueError: 当 endpoint、access_key_id 或 access_key_secret 配置缺失时抛出。
        """
        if not all([endpoint, access_key_id, access_key_secret]):
            raise ValueError("RustFS settings环境变量配置错误")
        # 根据 use_ssl 补全 endpoint 协议前缀
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"{'https' if use_ssl else 'http'}://{endpoint}"
        super().__init__(endpoint, access_key_id, access_key_secret, use_ssl)
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.access_key_secret,
            config=Config(
                signature_version="s3v4",
            )
        )

    def bucket_exists(self, name: str) -> bool:
        """判断指定名称的 Bucket 是否存在。

        Args:
            name (str): 需要检查的 Bucket 名称。

        Returns:
            bool: 如果 Bucket 存在返回 True，否则返回 False。
        """
        try:
            self._s3_client.head_bucket(Bucket=name)
            return True
        except ClientError:
            return False

    def get_bucket(self, name: str) -> Optional["RustfsBucket"]:
        """根据名称获取指定的 RustFS Bucket 实例。

        Args:
            name (str): 需要获取的 Bucket 名称。

        Returns:
            Optional[RustfsBucket]: 如果 Bucket 存在则返回其实例，否则返回 None。
        """
        if self.bucket_exists(name):
            return RustfsBucket(name=name, storage=self)
        return None

    def buckets(self) -> List["RustfsBucket"]:
        """获取当前账号下所有的 RustFS Bucket 列表。

        Returns:
            List[RustfsBucket]: 包含所有 Bucket 实例的列表。
        """
        response = self._s3_client.list_buckets()
        bucket_objs = []
        for bucket in response.get("Buckets", []):
            bucket_objs.append(RustfsBucket(name=bucket["Name"], storage=self))
        return bucket_objs

    def ensure_bucket(self, name: str) -> Optional["RustfsBucket"]:
        """确保指定名称的 Bucket 存在，若不存在则创建。

        Args:
            name (str): 需要确保存在的 Bucket 名称。

        Returns:
            Optional[RustfsBucket]: 创建或已存在的 Bucket 实例。
        """
        if not self.bucket_exists(name):
            self._s3_client.create_bucket(Bucket=name)
            logger.info(f"RustFS Bucket {name} 创建成功")
        return self.get_bucket(name)


class RustfsBucket(BaseBucket):
    """RustFS Bucket 封装类。

    继承自 BaseBucket，提供对特定 RustFS Bucket 的操作，
    包括文件的上传、下载、对象管理及 Bucket 自身的删除等。

    Attributes:
        _s3_client (boto3.client): 底层 boto3 S3 客户端实例。
    """

    def __init__(self, name: str, storage: RustfsStorage):
        """初始化 RustfsBucket 实例。

        Args:
            name (str): Bucket 的名称。
            storage (RustfsStorage): 关联的 RustfsStorage 存储客户端实例。
        """
        super().__init__(name, storage)
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.storage.endpoint,
            aws_access_key_id=self.storage.access_key_id,
            aws_secret_access_key=self.storage.access_key_secret,
            config=Config(
                signature_version="s3v4",
            )
        )

    def fput(self, local_path: str, object_key: str) -> None:
        """将本地文件上传至对象存储。

        Args:
            local_path (str): 本地文件的路径。
            object_key (str): 对象存储中的目标对象键（Object Key）。

        Raises:
            FileNotFoundError: 当本地文件不存在时抛出。
        """
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"RustFS 本地文件不存在: {local_path}")
        self._s3_client.upload_file(Filename=local_path,
                                    Bucket=self.name,
                                    Key=object_key)
        logger.info(f"RustFS 上传: {local_path} → {object_key}")

    def fget(self, object_key: str, local_path: str) -> None:
        """从对象存储下载文件到本地。

        Args:
            object_key (str): 对象存储中的对象键（Object Key）。
            local_path (str): 本地保存的目标文件路径。
        """
        self._s3_client.download_file(Bucket=self.name,
                                      Key=object_key,
                                      Filename=local_path)
        logger.info(f"RustFS 下载: {object_key} → {local_path}")

    def objects(self, prefix: str = "") -> List["RustfsObject"]:
        """列举 Bucket 中匹配指定前缀的所有对象。

        Args:
            prefix (str, optional): 对象键的前缀过滤条件。默认为空字符串，即列举所有对象。

        Returns:
            List[RustfsObject]: 包含所有匹配对象的 RustfsObject 实例列表。
        """
        obj_list = []
        response = self._s3_client.list_objects_v2(Bucket=self.name, Prefix=prefix)
        for obj in response.get("Contents", []):
            obj_list.append(RustfsObject(object_key=obj["Key"],
                                         bucket=self,
                                         storage=self.storage))
        return obj_list

    def delete(self) -> None:
        """删除当前 Bucket。

        如果 Bucket 不存在则仅记录警告日志，不执行删除操作。
        """
        if self.storage.bucket_exists(self.name):
            self._s3_client.delete_bucket(Bucket=self.name)
            logger.info(f"RustFS Bucket {self.name} deleted")
        else:
            logger.warning(f"RustFS Bucket {self.name} not exist, no need to delete")

    def delete_object(self, object_key: str) -> None:
        """删除指定对象。

        Args:
            object_key (str): 需要删除的对象键（Object Key）。
        """
        self._s3_client.delete_object(Bucket=self.name, Key=object_key)
        logger.info(f"RustFS 删除 object: {object_key}")

    def get_object(self, object_key: str) -> Optional["RustfsObject"]:
        """获取指定对象。

        Args:
            object_key (str): 需要获取的对象键（Object Key）。

        Returns:
            Optional[RustfsObject]: 如果对象存在则返回其实例，否则返回 None。
        """
        try:
            self._s3_client.head_object(Bucket=self.name, Key=object_key)
            return RustfsObject(object_key=object_key,
                                bucket=self,
                                storage=self.storage)
        except ClientError:
            return None

    def presigned_get_url(self, object_key: str, expires: int = 3600) -> str:
        """生成用于下载对象的预签名 URL。

        Args:
            object_key (str): 对象存储中的对象键（Object Key）。
            expires (int, optional): 预签名 URL 的有效期（秒）。默认为 3600 秒。

        Returns:
            str: 生成的预签名下载 URL。
        """
        return self._s3_client.generate_presigned_url(ClientMethod="get_object",
                                                      Params={"Bucket": self.name,
                                                              "Key": object_key},
                                                      ExpiresIn=expires)

    def presigned_put_url(self, object_key: str, expires: int = 3600) -> str:
        """生成用于上传对象的预签名 URL。

        Args:
            object_key (str): 对象存储中的目标对象键（Object Key）。
            expires (int, optional): 预签名 URL 的有效期（秒）。默认为 3600 秒。

        Returns:
            str: 生成的预签名上传 URL。
        """
        return self._s3_client.generate_presigned_url(ClientMethod="put_object",
                                                      Params={"Bucket": self.name,
                                                              "Key": object_key},
                                                      ExpiresIn=expires)


class RustfsObject(BaseObject):
    """RustFS Object 封装类。

    继承自 BaseObject，提供对特定 RustFS 对象的操作，
    包括对象的存在性检查及大小获取等。

    Attributes:
        _s3_client (boto3.client): 底层 boto3 S3 客户端实例。
    """

    def __init__(self, object_key: str, bucket: RustfsBucket, storage: RustfsStorage):
        """初始化 RustfsObject 实例。

        Args:
            object_key (str): 对象的名称（Object Key）。
            bucket (RustfsBucket): 对象所属的 RustfsBucket 实例。
            storage (RustfsStorage): 关联的 RustfsStorage 存储客户端实例。
        """
        super().__init__(object_key, bucket, storage)
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.storage.endpoint,
            aws_access_key_id=self.storage.access_key_id,
            aws_secret_access_key=self.storage.access_key_secret,
            config=Config(
                signature_version="s3v4",
            )
        )

    def exists(self) -> bool:
        """检查当前对象是否存在于 RustFS 中。

        Returns:
            bool: 如果对象存在返回 True，否则返回 False。
        """
        try:
            self._s3_client.head_object(Bucket=self.bucket_name, Key=self.name)
            return True
        except ClientError:
            return False

    @property
    def size(self) -> int:
        """获取当前对象的大小（字节数）。

        Returns:
            int: 对象的大小（字节数）。如果对象不存在则返回 -1。
        """
        try:
            response = self._s3_client.head_object(Bucket=self.bucket_name, Key=self.name)
            return response.get("ContentLength", -1)
        except ClientError:
            return -1
