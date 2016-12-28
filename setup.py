#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright © 2016 Alex Forster. All rights reserved.
# This software is licensed under the 3-Clause ("New") BSD license.
# See the LICENSE file for details.
#


from setuptools import setup


PACKAGE_NAME = 'sisqo'
PACKAGE_VERSION = '2.0.8'

setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    author='Alex Forster',
    author_email='alex@alexforster.com',
    maintainer='Alex Forster',
    maintainer_email='alex@alexforster.com',
    url='https://github.com/AlexForster/sisqo',
    description='A better library for automating network gear with Cisco-style command line interfaces',
    license='3-Clause ("New") BSD license',
    download_url='https://pypi.python.org/pypi/sisqo',
    packages=[PACKAGE_NAME],
    package_dir={PACKAGE_NAME: './sisqo'},
    package_data={PACKAGE_NAME: [
        'README*',
        'LICENSE',
        'requirements.txt',
    ]},
    install_requires=[
        'ptyprocess<0.6.0',
        'pyte<0.6.0',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
    ],
)
