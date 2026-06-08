import os


ALIYUN_STORAGE_CONFIG = {
    "access_key_id": os.getenv('ALIYUN_ACCESS_KEY_ID', ""),
    "access_key_secret": os.getenv('ALIYUN_ACCESS_KEY_SECRET', ""),
    "endpoint": os.getenv('ALIYUN_ENDPOINT', ""),
    "region": os.getenv('ALIYUN_REGION', ""),
    "aliyun_bucket": os.getenv('ALIYUN_BUCKET', ""), # aliyun的bucket就是storage, 不是共识的bucket
    "connect_timeout": int(os.getenv('ALIYUN_CONNECT_TIMEOUT', 10)),
    "use_ssl": os.getenv('ALIYUN_ENDPOINT_SSL', 'false').lower() in ('true', '1', 'yes'),
}

MINIO_STORAGE_CONFIG = {
    "access_key_id": os.getenv('MINIO_ACCESS_KEY_ID', ""),
    "access_key_secret": os.getenv('MINIO_ACCESS_KEY_SECRET', ""),
    "endpoint": os.getenv('MINIO_ENDPOINT', ""),
    "connect_timeout": int(os.getenv('MINIO_CONNECT_TIMEOUT', 10)),
    "read_timeout": int(os.getenv('MINIO_READ_TIMEOUT', 10)),
    "use_ssl": os.getenv('MINIO_ENDPOINT_SSL', 'false').lower() in ('true', '1', 'yes'),
}

RUSTFS_STORAGE_CONFIG = {
    "access_key_id": os.getenv('RUSTFS_ACCESS_KEY_ID', ""),
    "access_key_secret": os.getenv('RUSTFS_ACCESS_KEY_SECRET', ""),
    "endpoint": os.getenv('RUSTFS_ENDPOINT', ""),
    "use_ssl": os.getenv('RUSTFS_ENDPOINT_SSL', 'false').lower() in ('true', '1', 'yes'),
}