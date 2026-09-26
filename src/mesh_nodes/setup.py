from glob import glob

from setuptools import setup

package_name = 'mesh_nodes'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Patnana Tarun',
    maintainer_email='hansika9705@gmail.com',
    description='Explorer-side mesh relay for /map and /tf',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'explorer_relay = mesh_nodes.explorer_relay_node:main',
        ],
    },
)
