import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'usv_diagnostic_gui'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orjan',
    maintainer_email='orjan@todo.todo',
    description='USV Diagnostic GUI',
    license='TODO',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'usv_diagnostic_gui = usv_diagnostic_gui.main:main',
            'usv_external_pinger = usv_diagnostic_gui.usv_external_pinger:main',
        ],
    },
)