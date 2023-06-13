"""Setup for annoto XBlock."""

import os

from setuptools import setup


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()


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
    version='0.4.0',
    description='An XBlock for adding Annoto in-video collaboration solution to any video',
    long_description=README,
    license='Apache 2.0',
    author='Annoto',
    url='https://github.com/Annoto/xblock-in-video-collaboration',
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
