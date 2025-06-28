import pathlib
import shutil
import subprocess
import sys
import textwrap

import build.util
import pyproject_hooks
import pytest

import multistage_build

project_root = pathlib.Path(multistage_build.__file__).parent


def check_output_has_content(content: str, output: str) -> bool:
    if content in output:
        return True
    print(output)
    assert content in output, f'The content "{content}" does not appear in the output'
    return False


def install_multistage_build(environment_prefix: pathlib.Path) -> None:
    # If we are running with the `pyproject.toml` available, install using
    # that, otherwise install the directory and the dependencies manually.
    mutistage_root = pathlib.Path(__file__).absolute().parents[2]
    if (mutistage_root / 'pyproject.toml').exists():
        subprocess.check_call(
            [
                environment_prefix / 'bin' / 'python',
                '-m',
                'pip',
                'install',
                '--disable-pip-version-check',
                mutistage_root,
            ],
        )
    else:
        # Copy into site-packages
        python_dirs = list((environment_prefix / 'lib').glob('python*.*'))
        if len(python_dirs) != 1:
            raise ValueError("A single lib/python* directory was not found")
        sp_dir = python_dirs[0] / 'site-packages'
        shutil.copytree(mutistage_root / 'multistage_build', sp_dir / 'multistage_build')
        # Now install the dependencies
        subprocess.check_call(
            [
                environment_prefix / 'bin' / 'python',
                '-m',
                'pip',
                'install',
                '--disable-pip-version-check',
                'importlib_metadata >= 4.6 ; python_version < "3.10"',
                'tomli >= 1.1.0 ; python_version < "3.11"',
            ],
        )


def test_build_wheel__no_hooks(tmp_path):
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
        'importlib_metadata >= 4.6 ; python_version < "3.10"',
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
        import setuptools.build_meta

        def build_wheel(*args, **kwargs):
            print('My custom build function')
            return setuptools.build_meta.build_wheel(*args, **kwargs)
    '''),
    )

    pyprj = tmp_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
    [build-system]
    requires = [
        'setuptools',
        'wheel',
        'importlib_metadata >= 4.6 ; python_version < "3.10"',
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
    assert 'My custom build function' in out


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
        'importlib_metadata >= 4.6 ; python_version < "3.10"',
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
    assert 'Successfully built' in out


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
        'importlib_metadata >= 4.6 ; python_version < "3.10"',
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
        'importlib_metadata >= 4.6 ; python_version < "3.10"',
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
    subprocess.check_call(
        [sys.executable, '-m', 'venv', venv_dir],
        text=True,
    )

    out = subprocess.check_output([venv_dir / 'bin' / 'python', '-m', 'pip', 'install', '--editable', '.', '--verbose', '--disable-pip-version-check'], cwd=tmp_path, stderr=subprocess.STDOUT, text=True)
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
        'importlib_metadata >= 4.6 ; python_version < "3.10"',
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


@pytest.fixture(scope='session')
def entrypoint_venv(tmp_path_factory):
    venv_path = tmp_path_factory.mktemp("entrypoint-venv")
    subprocess.check_call([sys.executable, '-m', 'venv', venv_path])

    install_multistage_build(venv_path)
    subprocess.check_call([venv_path / 'bin' / 'python', '-m', 'pip', 'install', 'pip', 'setuptools>=65', 'wheel', 'build', '--disable-pip-version-check'])
    return venv_path


@pytest.fixture(scope='session')
def entrypoint_pkg(entrypoint_venv, tmp_path_factory):
    entrypoint_pkg = tmp_path_factory.mktemp('entrypoint-pkg')
    package_dir = entrypoint_pkg / 'test_entrypoint_pkg'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text(
        textwrap.dedent('''
        def build_wheel_hook(whl_path):
            print(f'EP build-wheel hook: {whl_path}')

        def build_editable_hook(whl_path):
            print(f'EP build-editable hook: {whl_path}')

        def prepare_metadata_for_build_wheel_hook(metadata_dir):
            print(f'EP prepare-metadata-for-build-wheel hook: {metadata_dir}')

        def build_sdist_hook(metadata_dir):
            print(f'EP build-sdist hook: {metadata_dir}')

    '''),
    )
    (entrypoint_pkg / 'pyproject.toml').write_text(
        textwrap.dedent('''
    [build-system]
    requires = ['setuptools>=65']
    build-backend = "setuptools.build_meta"

    [project]
    name = "test-entrypoint-pkg"
    version = "0.1.0"

    [project.entry-points.multistage_build]
    post-prepare-metadata-for-build-wheel = "test_entrypoint_pkg:prepare_metadata_for_build_wheel_hook"
    post-build-wheel = "test_entrypoint_pkg:build_wheel_hook"
    post-build-editable = "test_entrypoint_pkg:build_editable_hook"
    post-build-sdist = "test_entrypoint_pkg:build_sdist_hook"
    '''),
    )
    subprocess.check_call([entrypoint_venv / 'bin' / 'python', '-m', 'pip', 'install', entrypoint_pkg, '--no-build-isolation', '--disable-pip-version-check'])
    return entrypoint_pkg


@pytest.fixture
def entrypoint_using_pkg(tmp_path):
    prj_path = tmp_path / 'entrypoint-using-prj'
    prj_path.mkdir()
    pyprj = prj_path / 'pyproject.toml'
    pyprj.write_text(
        textwrap.dedent("""
        [build-system]
        requires = ['setuptools', 'multistage-build']
        build-backend = "multistage_build:backend"

        [tool.multistage-build]
        build-backend = "setuptools.build_meta"

        [project]
        name = "some-project"
        version = "0.1.0"
        """),
    )
    return prj_path


def test_build_wheel__entrypoint(entrypoint_venv, entrypoint_pkg, entrypoint_using_pkg):
    out = subprocess.check_output([entrypoint_venv / 'bin' / 'python', '-m', 'build', '--wheel', entrypoint_using_pkg, '--no-isolation', '--skip-dependency-check'], stderr=subprocess.STDOUT, text=True)
    assert check_output_has_content('EP build-wheel hook', out)


def test_build_editable__entrypoint(entrypoint_venv, entrypoint_pkg, entrypoint_using_pkg):
    out = subprocess.check_output([entrypoint_venv / 'bin' / 'python', '-m', 'pip', 'install', '--editable', entrypoint_using_pkg, '--no-build-isolation', '--disable-pip-version-check', '--verbose'], stderr=subprocess.STDOUT, text=True)
    assert check_output_has_content('EP build-editable hook', out)


def test_build_sdist__entrypoint(entrypoint_venv, entrypoint_pkg, entrypoint_using_pkg):
    out = subprocess.check_output([entrypoint_venv / 'bin' / 'python', '-m', 'build', '--sdist', entrypoint_using_pkg, '--no-isolation', '--skip-dependency-check'], stderr=subprocess.STDOUT, text=True)
    assert check_output_has_content('EP build-sdist hook', out)


def test_metadata__entrypoint(entrypoint_venv, entrypoint_pkg, entrypoint_using_pkg):
    out = subprocess.check_output(
        [
            entrypoint_venv / 'bin' / 'python',
            '-c',
            f'import build.util; import pyproject_hooks; build.util.project_wheel_metadata(source_dir="{entrypoint_using_pkg}", isolated=False, runner=pyproject_hooks.default_subprocess_runner)',
        ],
        text=True,
    )
    assert check_output_has_content('EP prepare-metadata-for-build-wheel hook', out)
