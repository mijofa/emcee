#!/usr/bin/python3
import setuptools
setuptools.setup(
    name='emcee',
    version='1.0',
    packages=['emcee'],
    package_data={'': ['*.css']},
    # This makes /usr/bin/emcee which is basically #!/bin/sh ↲ exec python3 -m emcee "$@"
    # Ref. https://packaging.python.org/tutorials/distributing-packages/#console-scripts
    # Ref. https://github.com/pypa/sampleproject
    entry_points={
        'console_scripts': ['emcee=emcee.__main__']
    }
)
