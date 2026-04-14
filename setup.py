#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Custom GNU Health
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import setup, find_packages

setup(
    name='gnuhealth_prescription_audit_v3',
    version='0.1',
    description='GNU Health Medication Audit Module - Prescription Selection',
    author='Custom Health Team',
    author_email='health@example.com',
    url='https://www.gnuhealth.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'gnuhealth',
        'trytond',
    ],
    entry_points={
        'trytond.modules': [
            'health_prescription_audit_v3 = health_prescription_audit_v3',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Intended Audience :: Healthcare Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Office/Business',
    ],
)
