from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("piano-capture")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["app", "util", "postprocess"]
