from importlib.machinery import PathFinder
import os
import pathlib
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib



HOOK_NAMES = {
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_wheel",
    "build_wheel",
    "get_requires_for_build_editable",
    "prepare_metadata_for_build_editable",
    "build_editable",
    "get_requires_for_build_sdist",
    "build_sdist",
    "_supported_features",
}

import typing


class BackendUnavailable(Exception):
    """Will be raised if the backend cannot be imported in the hook process."""
    def __init__(
        self,
        traceback: str,
        message: typing.Optional[str] = None,
        backend_name: typing.Optional[str] = None,
        backend_path: typing.Optional[typing.Sequence[str]] = None,
    ) -> None:
        # Preserving arg order for the sake of API backward compatibility.
        self.backend_name = backend_name
        self.backend_path = backend_path
        self.traceback = traceback
        super().__init__(message or "Error while importing backend")


class _BackendPathFinder:
    """Implements the MetaPathFinder interface to locate modules in ``backend-path``.

    Since the environment provided by the frontend can contain all sorts of
    MetaPathFinders, the only way to ensure the backend is loaded from the
    right place is to prepend our own.
    """

    def __init__(self, backend_path, backend_module):
        self.backend_path = backend_path
        self.backend_module = backend_module
        self.backend_parent, _, _ = backend_module.partition(".")

    def find_spec(self, fullname, _path, _target=None):
        if "." in fullname:
            # Rely on importlib to find nested modules based on parent's path
            return None

        # Ignore other items in _path or sys.path and use backend_path instead:
        spec = PathFinder.find_spec(fullname, path=self.backend_path)
        if spec is None and fullname == self.backend_parent:
            # According to the spec, the backend MUST be loaded from backend-path.
            # Therefore, we can halt the import machinery and raise a clean error.
            msg = f"Cannot find module {self.backend_module!r} in {self.backend_path!r}"
            raise BackendUnavailable(msg)

        return spec

from importlib import import_module
import traceback


def _build_backend(backend: str, *, backend_path: typing.Optional[str]):
    """Find and load the build backend"""

    # Taken from
    # https://github.com/pypa/pyproject-hooks/blob/v1.1.0/src/pyproject_hooks/_in_process/_in_process.py#L58-L78
    mod_path, _, obj_path = backend.partition(":")

    if backend_path:
        # Ensure in-tree backend directories have the highest priority when importing.
        extra_pathitems = backend_path.split(os.pathsep)
        sys.meta_path.insert(0, _BackendPathFinder(extra_pathitems, mod_path))

    try:
        obj = import_module(mod_path)
    except ImportError:
        msg = f"Cannot import {mod_path!r}"
        raise BackendUnavailable(msg, traceback.format_exc())

    if obj_path:
        for path_part in obj_path.split("."):
            obj = getattr(obj, path_part)
    return obj


class BuildBackend:
    def __init__(self):
        self._source_root = pathlib.Path.cwd()

    def _load_wrapped_backend(self):
        pyproject_content = tomllib.loads(
            (self._source_root / 'pyproject.toml').read_text(),
        )
        multistage_config = pyproject_content.get('tool', {}).get('multistage-build', {})
        build_backend = multistage_config['build-backend']
        backend_path = multistage_config.get('backend-path', [])

        return _build_backend(backend=build_backend, backend_path=':'.join(backend_path))

    def _load_build_wheel_hooks(self):
        pyproject_content = tomllib.loads(
            (self._source_root / 'pyproject.toml').read_text(),
        )
        multistage_config = pyproject_content.get('tool', {}).get('multistage-build', {})
        build_wheel_hooks = multistage_config.get('post-build-wheel', [])
        hooks = []
        for hook in build_wheel_hooks:
            if isinstance(hook, str):
                hook_function_ep = hook
                hook_path = None
            else:
                hook_function_ep = hook['hook-function']
                hook_path = hook.get('hook-path', [])
                if isinstance(hook_path, str):
                    hook_path = [hook_path]
            hooks.append(_build_backend(backend=hook_function_ep, backend_path=':'.join(hook_path)))
        return hooks

    def _load_build_editable_hooks(self):
        pyproject_content = tomllib.loads(
            (self._source_root / 'pyproject.toml').read_text(),
        )
        multistage_config = pyproject_content.get('tool', {}).get('multistage-build', {})
        declared_hooks = multistage_config.get('post-build-editable', [])
        hooks = []
        for hook in declared_hooks:
            if isinstance(hook, str):
                hook_function_ep = hook
                hook_path = None
            else:
                hook_function_ep = hook['hook-function']
                hook_path = hook.get('hook-path', [])
                if isinstance(hook_path, str):
                    hook_path = [hook_path]
            hooks.append(_build_backend(backend=hook_function_ep, backend_path=':'.join(hook_path)))
        return hooks

    def _load_prepare_metadata_for_build_wheel(self):
        pyproject_content = tomllib.loads(
            (self._source_root / 'pyproject.toml').read_text(),
        )
        multistage_config = pyproject_content.get('tool', {}).get('multistage-build', {})
        declared_hooks = multistage_config.get('post-prepare-metadata-for-build-wheel', [])
        hooks = []
        for hook in declared_hooks:
            if isinstance(hook, str):
                hook_function_ep = hook
                hook_path = None
            else:
                hook_function_ep = hook['hook-function']
                hook_path = hook.get('hook-path', [])
                if isinstance(hook_path, str):
                    hook_path = [hook_path]
            hooks.append(_build_backend(backend=hook_function_ep, backend_path=':'.join(hook_path)))
        return hooks

    @property
    def build_wheel(self):
        """Return the build wheel function for the backend, or raise AttributeError."""

        backend = self._load_wrapped_backend()

        def build_wheel(wheel_directory, config_settings=None, metadata_directory=None) -> str:
            wheel_name = backend.build_wheel(wheel_directory, config_settings, metadata_directory)
            wheel_path = pathlib.Path(wheel_directory) / wheel_name
            for hook in self._load_build_wheel_hooks():
                hook(wheel_path)
            return wheel_name
        return build_wheel

    @property
    def build_sdist(self):
        backend = self._load_wrapped_backend()
        def build_sdist(sdist_directory, config_settings=None):
            sdist_name = backend.build_sdist(sdist_directory, config_settings)
            sdist_path = pathlib.Path(sdist_directory) / sdist_name
            return sdist_name
        return build_sdist

    @property
    def get_requires_for_build_wheel(self):
        backend = self._load_wrapped_backend()
        return backend.get_requires_for_build_wheel

    @property
    def prepare_metadata_for_build_wheel(self):
        backend = self._load_wrapped_backend()
        def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
            dist_info_name = backend.prepare_metadata_for_build_wheel(metadata_directory, config_settings)
            dist_info_path = pathlib.Path(metadata_directory) / dist_info_name
            for hook in self._load_prepare_metadata_for_build_wheel():
                hook(dist_info_path)
            return dist_info_name
        return prepare_metadata_for_build_wheel

    @property
    def get_requires_for_build_sdist(self):
        backend = self._load_wrapped_backend()
        return backend.get_requires_for_build_sdist

    @property
    def build_editable(self):
        backend = self._load_wrapped_backend()
        # Raise if this doesn't exist on the backend.
        backend_build_editable = backend.build_editable

        def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
            result = backend_build_editable(wheel_directory, config_settings, metadata_directory)
            for hook in self._load_build_editable_hooks():
                hook(result)
            return result

        return build_editable

    @property
    def get_requires_for_build_editable(self):
        backend = self._load_wrapped_backend()
        return backend.get_requires_for_build_editable

    @property
    def prepare_metadata_for_build_editable(self):
        backend = self._load_wrapped_backend()
        return backend.prepare_metadata_for_build_editable
