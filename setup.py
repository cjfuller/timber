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
    scripts=['bin/timber']
)
