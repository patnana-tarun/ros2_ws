import os

from setuptools import find_packages, setup

package_name = 'explorer_bringup'
# ESP32 sketches go into share/ too, so they can be found (and compile-checked) on the Pi
firmware = [(os.path.join('share', package_name, d), [os.path.join(d, f) for f in files])
            for d, _, files in os.walk('firmware') if files]

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/robot.launch.py', 'launch/mapping.launch.py']),
        ('share/' + package_name + '/config', ['config/robot.yaml', 'config/slam.yaml',
                                               'config/mapping.rviz']),
    ] + firmware,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Patnana Tarun',
    maintainer_email='hansika9705@gmail.com',
    description='Real-robot bringup for the explorer: ESP32 bridge, X2 LiDAR driver, launch',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'esp32_bridge = explorer_bringup.esp32_bridge:main',
            'x2_lidar = explorer_bringup.x2_lidar:main',
            'fake_robot = explorer_bringup.fake_robot:main',
            'esp32_check = explorer_bringup.checks:esp32_check',
            'x2_check = explorer_bringup.checks:x2_check',
            'hw_selftest = explorer_bringup.selftest:main',
        ],
    },
)
