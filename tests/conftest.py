import os, subprocess, logging, pytest
from dotenv import load_dotenv
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.minio import MinioContainer
from testcontainers.milvus import MilvusContainer


@pytest.fixture(scope='session', autouse=True)
def configure_logging():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@pytest.fixture(scope="session", autouse=True)
def set_env():

    if not os.path.exists(os.path.expanduser("~/.wskprops")):
        raise pytest.UsageError("You need to login to execute integration tests")

    # load secrets
    command = ["ops", "-config", "-dump"]
    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout

    # Parse the output and set environment variables
    for line in output.splitlines():
        try:
            key, value = line.split('=', 1)
            os.environ[key] = value
            print("OK:", key)
        except:
            print("ERR:", line)

    # override with testenv
    load_dotenv(".env")
    load_dotenv("tests/.env", override=True)
    

@pytest.fixture(scope="session")    
def postgres():
    """
    Starts a Postgres container if ENABLE_POSTGRES=1 is set.
    Yields a running PostgresContainer instance.
    """
    if not os.getenv("ENABLE_POSTGRES"):
        pytest.skip("Postgres fixture disabled (set ENABLE_POSTGRES=1 to enable)")

    container = PostgresContainer("postgres:16-alpine").start()
    os.environ["POSTGRES_URL"] = container.get_connection_url().replace("+psycopg2", "", 1)
    yield container
    container.stop()

@pytest.fixture(scope="session")
def redis():
    """
    Starts a Redis container if ENABLE_REDIS=1 is set.
    Yields a running RedisContainer instance.
    """
    if not os.getenv("ENABLE_REDIS"):
        pytest.skip("Redis fixture disabled (set ENABLE_REDIS=1 to enable)")

    container = RedisContainer("redis:7").start()
    host = container.get_container_host_ip()
    port = container.get_exposed_port(6379)
    os.environ["REDIS_URL"] = f"redis://{host}:{port}"
    os.environ["REDIS_PREFIX"] = f"test:"
    yield container
    container.stop()
    
@pytest.fixture(scope="session")
def minio():
    """
    Starts a Minio container if ENABLE_MINIO=1 is set.
    Yields a running MinioContainer instance.
    """
    if not os.getenv("ENABLE_MINIO"):
        pytest.skip("MinIO fixture skipped (set ENABLE_MINIO=1 to enable)")

    container = MinioContainer("minio/minio:latest").start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(9000)
    access_key = container.access_key
    secret_key = container.secret_key
    bucket = "data"

    # Set environment variables
    os.environ["S3_HOST"] = host
    os.environ["S3_PORT"] = str(port)
    os.environ["S3_ACCESS_KEY"] = access_key
    os.environ["S3_SECRET_KEY"] = secret_key
    os.environ["S3_BUCKET_DATA"] = bucket
    
    yield container
    container.stop()

@pytest.fixture(scope="session")
def milvus():
    """
    Starts a Milvus container if ENABLE_MILVUS=1 is set.
    Yields a running MilvusContainer instance.
    """
    if not os.getenv("ENABLE_MILVUS"):
        pytest.skip("Milvus fixture skipped (set ENABLE_MILVUS=1 to enable)")

    container = MilvusContainer("milvusdb/milvus:2.4.3").start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(19530)

    # Set env vars
    os.environ["MILVUS_HOST"] = host
    os.environ["MILVUS_PORT"] = str(port)
    os.environ["MILVUS_DB_NAME"] = "default"
    os.environ["MILVUS_TOKEN"] = ""   # can be set if auth is enabled

    yield container
    container.stop()