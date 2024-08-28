# multistage-build

A generic PEP-517 build backend which allows additional processing to be applied
to the resulting metadata, wheel and/or editable wheel.

## Motivating Example

Sometimes it is desirable to run a post-processing step on a built wheel. For
example, we may wish to inject some additional metadata into the wheel. To do
this, we should write a function which accepts the wheel path as its only
argument, for example:

```
def my_wheel_post_processing_func(wheel_path):
    print(f'The wheel to be processed is at {wheel_path}')
```

This function can then be declared as post-processing step of the PEP-517
`build_wheel` function:

```
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

```
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

## Status of work

The current functionality includes:

 * Hooks for build-wheel
 * Ability to have local definitions included, using the same mechanism as
   in-source builds from PEP-517.

There are a few known features not yet implemented:

 * Hooks for sdist
 * Hooks for all other PEP-517 and PEP-660 hooks
