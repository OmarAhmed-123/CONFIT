from .local_catvton import LocalCatVtonBackend
from .local_idmvton import LocalIdmVtonBackend
from .remote_gpu import RemoteGPUBackend
from .replicate_backend import ReplicateBackend
from .fashn_backend import FashnBackend
from .huggingface_space import HuggingFaceSpaceBackend

__all__ = [
    "LocalCatVtonBackend",
    "LocalIdmVtonBackend",
    "RemoteGPUBackend",
    "ReplicateBackend",
    "FashnBackend",
    "HuggingFaceSpaceBackend",
]

