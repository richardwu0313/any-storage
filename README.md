# any-storage

A generic OSS storage access library. Provides a unified abstraction layer for multiple object storage services (Aliyun OSS, MinIO), enabling consistent bucket and object operations across different storage backends.

## Features

- **Unified API**: Abstract `BaseStorage`, `BaseBucket`, `BaseObject` interfaces for consistent operations across storage backends
- **Factory Pattern**: `create_storage()` factory method to create storage instances by type or environment variable
- **Supported Backends**:
  - Aliyun OSS (via `oss2`)
  - MinIO (via `minio`)
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

# Via environment variable STORAGE=aliyun or STORAGE=minio
StorageCls = create_storage()

# Or explicitly specify the storage type
StorageCls = create_storage("aliyun")
StorageCls = create_storage("minio")
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

## Development

### Setup

```bash
uv sync --extra test
```

### Running Tests

```bash
pytest
```

### Local MinIO for Testing

A `compose.yml` is provided for running a local MinIO instance:

```bash
docker compose up -d
```

## Requirements

- Python >= 3.13
- loguru >= 0.7.3
- minio >= 7.2.20
- oss2 >= 2.19.1

## License

See project repository for license information.