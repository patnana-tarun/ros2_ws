from setuptools import find_packages, setup

package_name = 'explorer_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/robot.launch.py']),
        ('share/' + package_name + '/config', ['config/robot.yaml']),
    ],
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
        ],
    },
)
