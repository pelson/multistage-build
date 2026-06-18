# multistage-build

A generic PEP-517 build backend which allows additional processing to be applied
to the resulting metadata, wheel and/or editable wheel.

## Motivating Example

Sometimes it is desirable to run a post-processing step on a built wheel. For
example, we may wish to inject some additional metadata into the wheel. To do
this, we should write a function which accepts the wheel path as its only
argument, for example:

```python
def my_wheel_post_processing_func(wheel_path):
    print(f'The wheel to be processed is at {wheel_path}')
```

This function can then be declared as post-processing step of the PEP-517
`build_wheel` function:

```toml
[build-system]
requires = [
    'multistage-build',
    'setuptools',
]
build-backend = "multistage_build:backend"

[tool.multistage-build]
build-backend = "setuptools.build_meta"
post-build-wheel = [
    {hook-function="my_mod:my_wheel_post_processing_func", hook-path="."},
]

[project]
name = "some-project"
version = "0.1.0"
...
```

We could also publish this functionality to the package repository, and consume
it by declaring it as a build requirement:

```toml
[build-system]
requires = [
    'multistage-build',
    'my_mod',
    'setuptools',
]
build-backend = "multistage_build:backend"

[tool.multistage-build]
build-backend = "setuptools.build_meta"
post-build-wheel = [
    "my_mod:my_wheel_post_processing_func",
]

[project]
name = "some-project"
version = "0.1.0"
...
```


## Plugin based hooks

For tools wishing to expose a standard behaviour, without requiring the user to
declare each of the hooks manually, it is possible to declare potential hooks
as entrypoints.

An example of a project which automatically registers build-time hooks using entry points:

```toml
[project.entry-points.multistage_build]
post-prepare-metadata-for-build-wheel = "my_mod:prepare_metadata_for_build_wheel_fn"
post-build-sdist = "my_mod:build_editable_fn"
post-build-wheel = "my_mod:build_editable_fn"
post-build-editable = "my_mod:build_wheel_fn"
```

These hooks will get called for any user of the multistage_build backend, even if
the project declaring these entrypoints doesn't itself use multistage-build.
It allows one to build a library of hooks, and to have consumers add them by
adding extra build dependencies (and declaring a multistage-build backend).

As is normal for entry-points, the name of the function is unimportant.
It is possible to declare multiple entry-points per hook.
A nice pattern would be to only run some behaviour if the hook is configured
in the `pyproject.toml` (which is in the CWD when the hook is running); though
this isn't obligatory (esp. when no configuration is needed - in that case,
the existence of the project in the build environment is enough of a signal for
the hook to be run).

## Hook points

For each PEP-517 / PEP-660 hook that multistage-build wraps, there is a `pre-*`
and a `post-*` extension point. Pre-hooks run before the wrapped backend is
invoked; post-hooks run after it returns. Use `pre-*` when you need to mutate
inputs (e.g. rewrite `pyproject.toml`) before the underlying backend reads
them. Use `post-*` when you want to operate on the produced artefact.

| Hook | When it fires | Arguments |
|------|---------------|-----------|
| `pre-build-wheel`  | Before `build_wheel`  | `(wheel_directory, config_settings)` |
| `post-build-wheel` | After `build_wheel`   | `(wheel_path,)` |
| `pre-build-editable`  | Before `build_editable`  | `(wheel_directory, config_settings)` |
| `post-build-editable` | After `build_editable`   | `(wheel_path,)` |
| `pre-build-sdist`  | Before `build_sdist`  | `(sdist_directory, config_settings)` |
| `post-build-sdist` | After `build_sdist`   | `(sdist_path,)` |
| `pre-prepare-metadata-for-build-wheel`  | Before `prepare_metadata_for_build_wheel`  | `(metadata_directory, config_settings)` |
| `post-prepare-metadata-for-build-wheel` | After `prepare_metadata_for_build_wheel`   | `(dist_info_path,)` |
| `pre-prepare-metadata-for-build-editable`  | Before `prepare_metadata_for_build_editable`  | `(metadata_directory, config_settings)` |
| `post-prepare-metadata-for-build-editable` | After `prepare_metadata_for_build_editable`   | `(dist_info_path,)` |

`config_settings` is the dict (or `None`) passed by the PEP-517 frontend. The
`*_directory` arguments are the directories where the artefact will be
written; they may not yet exist, and certainly do not yet contain the
artefact.

Each hook can be declared either inline in `pyproject.toml` under
`[tool.multistage-build]`, or via the `multistage_build` entry-point group on
an installed package. The `pre-*` hooks follow the same patterns as the
`post-*` hooks documented above, under the matching name.

## Status of work

The current functionality includes:

 * Pre- and post- hooks for `build-wheel`, `build-editable`, `build-sdist`,
   `prepare-metadata-for-build-wheel`, and `prepare-metadata-for-build-editable`.
 * Ability to have local definitions included, using the same mechanism as
   in-source builds from PEP-517.

There are a few known features not yet implemented:

 * Ability to override multiple hooks with a single declaration (e.g. editable and build hooks). Perhaps allow entrypoint definitions so that you get it simply by having the dependency installed?
