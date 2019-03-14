"""Setup for annoto XBlock."""

import os

from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='annoto-xblock',
    version='0.1.0',
    description='An XBlock for adding Annoto in-video collaboration solution to any video',
    license='Apache 2.0',
    packages=[
        'annoto',
    ],
    install_requires=[
        'XBlock',
        'xblock_utils',
        'PyJWT',
    ],
    entry_points={
        'xblock.v1': [
            'annoto = annoto:AnnotoXBlock',
        ]
    },
    package_data=package_data("annoto", ["static", "public", "translations"]),
)
