from setuptools import find_packages
from setuptools import setup

setup(
    name='my_mesh_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('my_mesh_interfaces', 'my_mesh_interfaces.*')),
)
