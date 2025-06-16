"""
Tests for the multistage_build package.

"""

import multistage_build


def test_version():
    # Check tha the package has a __version__ attribute.
    assert multistage_build.__version__ is not None
