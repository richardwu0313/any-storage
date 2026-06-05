from enum import StrEnum


class StorageEnum(StrEnum):
    ALIYUN = "aliyun"
    MINIO = "minio"
    RUSTFS = "rustfs"