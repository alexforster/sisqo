#!/usr/bin/env python
# -*- coding: utf-8 -*-
########################################################################################################################
# Copyright © 2015 Alex Forster. All rights reserved.
# This software is licensed under the 3-Clause ("New") BSD license.
# See the LICENSE file for details.
########################################################################################################################


from setuptools import setup


PACKAGE_NAME = 'sisqo'
PACKAGE_VERSION = '1.0.4'

setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    author='Alex Forster',
    author_email='alex@alexforster.com',
    maintainer='Alex Forster',
    maintainer_email='alex@alexforster.com',
    url='https://github.com/AlexForster/sisqo',
    description='More friendly access to Cisco-style CLIs from Python',
    license='3-Clause ("New") BSD license',
    download_url='https://pypi.python.org/pypi/sisqo',
    packages=[PACKAGE_NAME],
    package_dir={PACKAGE_NAME: '.'},
    package_data={PACKAGE_NAME: [
        'README*',
        'LICENSE',
        'requirements.txt',
    ]},
    install_requires=[
        'paramiko<2.0.0',
        'pyte<0.6.0',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: C',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
    ],
)
