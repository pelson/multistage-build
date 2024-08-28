"""
Documentation for the multistage_build package

"""
# Import the version from the generated _version.py file. __version__ is part
# of the public API, and we therefore ignore the "unused" (F401) lint warning.
from ._version import __version__  # noqa: F401  # pylint: disable=import-error

from ._build_backend import BuildBackend as _BuildBackend

# Expose the backend as `multistage_build:backend` as described in PEP-517.
backend = _BuildBackend()
