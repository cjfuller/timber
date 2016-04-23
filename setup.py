#!/usr/bin/env python

from setuptools import setup

setup(
    name='timber',
    version='0.2.0',
    description='Command line viewer for Google cloud logging',
    author='Colin Fuller',
    author_email='colin@khanacademy.org',
    url='https://github.com/cjfuller/timber',
    packages=['timber'],
    scripts=['bin/timber'],
    install_requires=[
        'blessed>=1.14.0,<1.15.0',
        'aiohttp==0.21.5',
        'funcy>=1.7.0,<1.8.0',
    ],
    keywords=['logging'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
    ]
)
