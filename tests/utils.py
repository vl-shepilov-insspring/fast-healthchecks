import atexit
import os
import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

__all__ = (
    "SSLCERT_NAME",
    "SSLKEY_NAME",
    "SSLROOTCERT_NAME",
    "create_temp_files",
)


SSLCERT_NAME = "cert.crt"
SSLKEY_NAME = "key.key"
SSLROOTCERT_NAME = "ca.crt"
TEST_CERT_LOCATION = Path(__file__).parent / "certs"

SSL_FILES_MAP = {
    SSLCERT_NAME: TEST_CERT_LOCATION / SSLCERT_NAME,
    SSLKEY_NAME: TEST_CERT_LOCATION / SSLKEY_NAME,
    SSLROOTCERT_NAME: TEST_CERT_LOCATION / SSLROOTCERT_NAME,
}


temp_dir = Path(tempfile.gettempdir()) / f"fast_healthchecks-{os.getpid()}"
temp_dir.mkdir(parents=True, exist_ok=True)
atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

TEST_SSLCERT = quote(str(temp_dir / SSLCERT_NAME))
TEST_SSLKEY = quote(str(temp_dir / SSLKEY_NAME))
TEST_SSLROOTCERT = quote(str(temp_dir / SSLROOTCERT_NAME))


def _try_rmdir(path: Path) -> bool:
    try:
        path.rmdir()
    except OSError:
        return False
    else:
        return True


def _remove_empty_parents(p: Path, boundary: Path) -> None:
    parent = p.parent
    while parent != boundary and boundary in parent.parents and parent.exists():
        if not _try_rmdir(parent):
            break
        parent = parent.parent


@contextmanager
def create_temp_files(temp_file_paths: list[str]) -> Generator[None, None, None]:
    paths = [Path(temp_file_path) for temp_file_path in temp_file_paths]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.name in SSL_FILES_MAP:
            shutil.copyfile(SSL_FILES_MAP[path.name], path)
        else:
            with path.open("w") as f:
                f.write("Temporary content.")
                f.flush()

    yield

    for path in paths:
        path.unlink(missing_ok=True)

    for path in paths:
        _remove_empty_parents(path, temp_dir)
