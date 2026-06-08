# any-storage

A generic OSS storage access library. Provides a unified abstraction layer for multiple object storage services (Aliyun OSS, MinIO, RustFS), enabling consistent bucket and object operations across different storage backends.

## Features

- **Unified API**: Abstract `BaseStorage`, `BaseBucket`, `BaseObject` interfaces for consistent operations across storage backends
- **Factory Pattern**: `create_storage()` factory method to create storage instances by type or environment variable
- **Presigned URLs**: Generate presigned GET/PUT URLs for temporary access without exposing credentials
- **Supported Backends**:
  - Aliyun OSS (via `oss2`)
  - MinIO (via `minio`)
  - RustFS (via `boto3`, S3-compatible)
- **Environment-based Configuration**: All connection parameters configurable via environment variables

## Installation

```bash
pip install any-storage
```

Or with `uv`:

```bash
uv add any-storage
```

## Quick Start

### Using the Factory Method

```python
from anystorage.storage import create_storage

# Via environment variable STORAGE=aliyun|minio|rustfs
StorageCls = create_storage()

# Or explicitly specify the storage type
StorageCls = create_storage("aliyun")
StorageCls = create_storage("minio")
StorageCls = create_storage("rustfs")
```

### Aliyun OSS

```python
from anystorage.contrib.aliyun_storage import AliyunStorage

storage = AliyunStorage()  # reads from environment variables
bucket = storage.ensure_bucket("my-bucket")

# Upload a file
bucket.fput("/local/path/file.txt", "remote-key.txt")

# Download a file
bucket.fget("remote-key.txt", "/local/path/downloaded.txt")

# List objects
objects = bucket.objects(prefix="prefix/")

# Presigned URL
get_url = bucket.presigned_get_url("remote-key.txt", expires=3600)
put_url = bucket.presigned_put_url("upload-key.txt", expires=3600)

# Check bucket existence
exists = storage.bucket_exists("my-bucket")
```

### MinIO

```python
from anystorage.contrib.minio_storage import MinioStorage

storage = MinioStorage()  # reads from environment variables
bucket = storage.ensure_bucket("my-bucket")

# Upload a file
bucket.fput("/local/path/file.txt", "remote-key.txt")

# Download a file
bucket.fget("remote-key.txt", "/local/path/downloaded.txt")

# List objects
objects = bucket.objects(prefix="prefix/")

# Presigned URL
get_url = bucket.presigned_get_url("remote-key.txt", expires=3600)
put_url = bucket.presigned_put_url("upload-key.txt", expires=3600)

# Check bucket existence
exists = storage.bucket_exists("my-bucket")
```

### RustFS

```python
from anystorage.contrib.rustfs_storage import RustfsStorage

storage = RustfsStorage()  # reads from environment variables
bucket = storage.ensure_bucket("my-bucket")

# Upload a file
bucket.fput("/local/path/file.txt", "remote-key.txt")

# Download a file
bucket.fget("remote-key.txt", "/local/path/downloaded.txt")

# List objects
objects = bucket.objects(prefix="prefix/")

# Presigned URL (S3-compatible)
get_url = bucket.presigned_get_url("remote-key.txt", expires=3600)
put_url = bucket.presigned_put_url("upload-key.txt", expires=3600)

# Check bucket existence
exists = storage.bucket_exists("my-bucket")
```

## Configuration

### Aliyun OSS Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ALIYUN_ACCESS_KEY_ID` | Aliyun AccessKey ID | `""` |
| `ALIYUN_ACCESS_KEY_SECRET` | Aliyun AccessKey Secret | `""` |
| `ALIYUN_ENDPOINT` | Aliyun OSS Endpoint | `""` |
| `ALIYUN_REGION` | Aliyun OSS Region | `""` |
| `ALIYUN_ENDPOINT_SSL` | Use SSL connection | `false` |
| `ALIYUN_CONNECT_TIMEOUT` | Connection timeout (seconds) | `10` |

### MinIO Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MINIO_ACCESS_KEY_ID` | MinIO Access Key ID | `""` |
| `MINIO_ACCESS_KEY_SECRET` | MinIO Secret Access Key | `""` |
| `MINIO_ENDPOINT` | MinIO Endpoint | `""` |
| `MINIO_ENDPOINT_SSL` | Use SSL connection | `false` |
| `MINIO_CONNECT_TIMEOUT` | Connection timeout (seconds) | `10` |
| `MINIO_READ_TIMEOUT` | Read timeout (seconds) | `10` |

### RustFS Environment Variables

| Variable | Description | Default |
|---|---|---|
| `RUSTFS_ACCESS_KEY_ID` | RustFS Access Key ID | `""` |
| `RUSTFS_ACCESS_KEY_SECRET` | RustFS Secret Access Key | `""` |
| `RUSTFS_ENDPOINT` | RustFS Endpoint | `""` |
| `RUSTFS_ENDPOINT_SSL` | Use SSL connection | `false` |

## Architecture

```
BaseStorage (ABC)
├── bucket_exists(name) -> bool
├── get_bucket(name) -> BaseBucket | None
├── buckets() -> List[BaseBucket]
├── ensure_bucket(name) -> BaseBucket
│
BaseBucket (ABC)
├── fput(local_path, object_key) -> None
├── fget(object_key, local_path) -> None
├── presigned_get_url(object_key, expires) -> str
├── presigned_put_url(object_key, expires) -> str
├── objects(prefix) -> List[BaseObject]
├── delete() -> None
├── delete_object(object_key) -> None
│
BaseObject (ABC)
├── exists() -> bool
├── size -> int
```

Implemented by:
- `AliyunStorage` / `AliyunBucket` / `AliyunObject`
- `MinioStorage` / `MinioBucket` / `MinioObject`
- `RustfsStorage` / `RustfsBucket` / `RustfsObject`

## Development

### Setup

```bash
uv sync --extra test
```

### Running Tests

```bash
pytest
```

### Local MinIO / RustFS for Testing

A `compose.yml` is provided for running local MinIO and RustFS instances:

```bash
docker compose up -d
```

- MinIO API: `http://localhost:19000` | Console: `http://localhost:19001`
- RustFS API: `http://localhost:29000` | Console: `http://localhost:29001`

## Requirements

- Python >= 3.13
- boto3 >= 1.43.23
- loguru >= 0.7.3
- minio >= 7.2.20
- oss2 >= 2.19.1

## License

See project repository for license information.
