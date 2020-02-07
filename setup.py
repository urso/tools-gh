# from distutils.core import setup
from setuptools import setup, find_packages

setup(
    name='worktools',
    version='0.1dev',
    packages=find_packages(),
    install_requires=[
        'gitpython',
        'requests',
        'gql',
        'python-editor',
        'clidec',
    ],
    entry_points={
        'console_scripts': [
            'gh = gh.__main__:main',
        ],
    },
)
