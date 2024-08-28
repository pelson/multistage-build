import pathlib
import shutil
import subprocess
import sys
import textwrap

import build.util
import pyproject_hooks

import multistage_build

project_root = pathlib.Path(multistage_build.__file__).parent

def test_build_wheel__no_hooks(tmp_path):
    print(project_root)
    backend_root = tmp_path / 'backend-root'
    backend_root.mkdir(exist_ok=False)
    shutil.copytree(project_root, backend_root / 'multistage_build')
    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'tomli >= 1.1.0 ; python_version < "3.11"',
    ]
    build-backend = "multistage_build:backend"
    backend-path = ["backend-root"]

    [tool.multistage-build]
    build-backend = "setuptools.build_meta"

    [project]
    name = "some-project"
    version = "0.1.0"
    """),
    )

    # TODO: Capture the wheel, and validate it.
    try:
        out = subprocess.check_output([sys.executable, '-m', 'build', '--wheel', '.'], cwd=tmp_path, text=True)
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise
    assert 'Successfully built' in out


def test_build_wheel__build_backend_path(tmp_path):
    backend_root = tmp_path / 'backend-root'
    backend_root.mkdir(exist_ok=False)
    shutil.copytree(project_root, backend_root / 'multistage_build')

    another_backend_root = tmp_path / 'backend-root2'
    another_backend_root.mkdir(exist_ok=False)

    (another_backend_root / 'setuptools_wrapper.py').write_text(
        textwrap.dedent('''
        from setuptools.build_meta import *
    '''),
    )

    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'tomli >= 1.1.0 ; python_version < "3.11"',
    ]
    build-backend = "multistage_build:backend"
    backend-path = ["backend-root"]

    [tool.multistage-build]
    build-backend = "setuptools_wrapper"
    backend-path = ["backend-root2"]

    [project]
    name = "some-project"
    version = "0.1.0"
    """),
    )

    # TODO: Capture the wheel, and validate it.
    out = subprocess.check_output(
        [sys.executable, '-m', 'build', '--wheel', '.'], cwd=tmp_path,
        text=True,
    )
    assert 'Successfully built' in out


def test_build_wheel__simple_hook(tmp_path):
    backend_root = tmp_path / 'backend-root'
    backend_root.mkdir(exist_ok=False)
    shutil.copytree(project_root, backend_root / 'multistage_build')
    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'tomli >= 1.1.0 ; python_version < "3.11"',
    ]
    build-backend = "multistage_build:backend"
    backend-path = ["backend-root"]

    [tool.multistage-build]
    build-backend = "setuptools.build_meta"
    post-build-wheel = [
        "pprint:pprint",
    ]

    [project]
    name = "some-project"
    version = "0.1.0"
    """),
    )

    # TODO: Capture the wheel, and validate it.
    out = subprocess.check_output([sys.executable, '-m', 'build', '--wheel', '.'], cwd=tmp_path, text=True)
    assert 'PosixPath(' in out


def test_build_wheel__hook_with_path(tmp_path):
    backend_root = tmp_path / 'backend-root'
    backend_root.mkdir(exist_ok=False)
    shutil.copytree(project_root, backend_root / 'multistage_build')

    another_backend_root = tmp_path / 'backend-root2'
    another_backend_root.mkdir(exist_ok=False)

    (another_backend_root / 'some_mod.py').write_text(
        textwrap.dedent('''
        def some_func(whl_path):
            print(f'Some func given wheel: {whl_path}')

        def another_func(whl_path):
            print(f'Another func given wheel: {whl_path}')
    '''),
    )

    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'tomli >= 1.1.0 ; python_version < "3.11"',
    ]
    build-backend = "multistage_build:backend"
    backend-path = ["backend-root"]

    [tool.multistage-build]
    build-backend = "setuptools.build_meta"
    post-build-wheel = [
        {hook-function="some_mod:some_func", hook-path=["backend-root2"]},
        {hook-function="some_mod:another_func", hook-path="backend-root2"},
    ]

    [project]
    name = "some-project"
    version = "0.1.0"
    """),
    )

    # TODO: Capture the wheel, and validate it.
    out = subprocess.check_output([sys.executable, '-m', 'build', '--wheel', '.'], cwd=tmp_path, text=True)
    assert 'Some func given wheel' in out
    assert 'Another func given wheel' in out


def test_build_editable__hook_with_path(tmp_path):
    backend_root = tmp_path / 'backend-root'
    backend_root.mkdir(exist_ok=False)
    shutil.copytree(project_root, backend_root / 'multistage_build')

    another_backend_root = tmp_path / 'backend-root2'
    another_backend_root.mkdir(exist_ok=False)

    (another_backend_root / 'some_mod.py').write_text(
        textwrap.dedent('''
        def another_func(whl_path):
            print(f'Another func given wheel: {whl_path}')
    '''),
    )

    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'tomli >= 1.1.0 ; python_version < "3.11"',
    ]
    build-backend = "multistage_build:backend"
    backend-path = ["backend-root"]

    [tool.multistage-build]
    build-backend = "setuptools.build_meta"
    post-build-editable = [
        {hook-function="some_mod:another_func", hook-path="backend-root2"},
    ]

    [project]
    name = "some-project"
    version = "0.1.0"
    """),
    )

    venv_dir = tmp_path / 'venv'
    out = subprocess.check_output(
        [sys.executable, '-m', 'venv', venv_dir],
        text=True,
    )

    # TODO: Capture the wheel, and validate it.
    out = subprocess.check_output([venv_dir / 'bin' / 'python', '-m', 'pip', 'install', '--editable', '.', '--verbose'], cwd=tmp_path, stderr=subprocess.STDOUT, text=True)
    assert 'Another func given wheel' in out


def test_prepare_metadata__hook_with_path(tmp_path, capfd):
    backend_root = tmp_path / 'backend-root'
    backend_root.mkdir(exist_ok=False)
    shutil.copytree(project_root, backend_root / 'multistage_build')

    another_backend_root = tmp_path / 'backend-root2'
    another_backend_root.mkdir(exist_ok=False)

    (another_backend_root / 'some_mod.py').write_text(
        textwrap.dedent('''
        def another_func(dist_info_path):
            print(f'Prepare metadata called and hooked: {dist_info_path}')
    '''),
    )

    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'tomli >= 1.1.0 ; python_version < "3.11"',
    ]
    build-backend = "multistage_build:backend"
    backend-path = ["backend-root"]

    [tool.multistage-build]
    build-backend = "setuptools.build_meta"
    post-prepare-metadata-for-build-wheel = [
        {hook-function="some_mod:another_func", hook-path="backend-root2"},
    ]

    [project]
    name = "some-project"
    version = "0.1.0"
    """),
    )

    build.util.project_wheel_metadata(source_dir=tmp_path, isolated=True, runner=pyproject_hooks.default_subprocess_runner)
    out, err = capfd.readouterr()
    assert 'Prepare metadata called and hooked' in out
