"""存储工厂模块。

提供根据环境变量或参数创建对应存储实例的工厂方法。
"""
import os
from typing import Optional

from anystorage.enums import StorageEnum
from anystorage.base import BaseStorage
from anystorage.contrib.aliyun_storage import AliyunStorage
from anystorage.contrib.minio_storage import MinioStorage


# 支持的存储类型注册表
_STORAGE_REGISTRY: dict[str, type[BaseStorage]] = {
    StorageEnum.ALIYUN: AliyunStorage,
    StorageEnum.MINIO: MinioStorage,
}


def create_storage(storage_type: Optional[str] = None) -> type[AliyunStorage] | type[MinioStorage] :
    """根据存储类型创建对应的存储实例。

    通过环境变量 STORAGE 指定存储类型，也可通过 storage_type 参数显式指定，
    参数优先级高于环境变量。

    Args:
        storage_type (str, optional): 存储类型，对应 StorageEnum 中的值。
            若为 None 则从环境变量 STORAGE 读取。

    Returns:
        BaseStorage: 对应的存储实例（AliyunStorage 或 MinioStorage）。

    Raises:
        ValueError: 当 storage_type 为空或不支持时抛出。
    """
    storage_type = storage_type or os.getenv("STORAGE", "")
    if not storage_type:
        raise ValueError(
            f"存储类型未指定，请设置环境变量 STORAGE 或传入 storage_type 参数，"
            f"支持的类型: {list(_STORAGE_REGISTRY.keys())}"
        )

    storage_type = storage_type.lower()
    storage_cls = _STORAGE_REGISTRY.get(storage_type)
    if storage_cls is None:
        raise ValueError(
            f"不支持的存储类型: {storage_type}，"
            f"支持的类型: {list(_STORAGE_REGISTRY.keys())}"
        )

    return storage_cls
