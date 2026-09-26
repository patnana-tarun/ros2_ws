from setuptools import find_packages, setup

package_name = 'explorer_exploration'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            ['launch/explore.launch.py', 'launch/bringup.launch.py',
             'launch/benchmark_headless.launch.py']),
        ('share/' + package_name + '/config', ['config/nav2_params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='monesh',
    maintainer_email='you@example.com',
    description='Frontier detection, TAD scoring, and exploration coordination',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'frontier_tad_node = explorer_exploration.frontier_tad_node:main',
            'explore_coordinator = explorer_exploration.explore_coordinator:main',
            'metrics_logger = explorer_exploration.metrics_logger:main',
        ],
    },
)
