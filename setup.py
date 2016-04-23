#!/usr/bin/env python

from setuptools import setup

setup(
    name='timber',
    version='0.1',
    description='Command line viewer for Google cloud logging',
    author='Colin Fuller',
    author_email='colin@khanacademy.org',
    url='',
    packages=['timber'],
    scripts=['bin/timber'],
    install_requires=[
        'blessed>=1.14.0,<1.15.0',
        'aiohttp==0.21.5',
        'funcy>=1.7.0,<1.8.0',
    ]
)
