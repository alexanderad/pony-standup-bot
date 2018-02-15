#!/usr/bin/env python
import re

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

version_regex = re.compile("VERSION\s*=\s*'(.*?)'$")
with open('pony/__init__.py') as stream:
    VERSION = version_regex.search(stream.read()).group(1)


setup(
    name='pony-standup-bot',
    version=VERSION,
    description='Tiny Standup Bot for Slack',
    long_description=readme,
    url='https://github.com/alexanderad/pony-standup-bot',
    license='MIT',
    author='Alexander Shchapov',
    author_email='alexander.shchapov@gmail.com',
    packages=find_packages(),
    package_data={'': ['LICENSE', 'README.rst']},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'pony=pony.runner:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
)
