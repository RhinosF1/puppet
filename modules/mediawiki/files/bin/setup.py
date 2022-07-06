"""Controls the setup of the package by setuptools/pip."""
from setuptools import find_packages, setup

with open('requirements.txt') as requirements_file:
    requirements = list(requirements_file.readlines())

with open('dev-requirements.txt') as dev_requirements_file:
    dev_requirements = list(dev_requirements_file.readlines())

setup(
    name='MW_SRE_Utils',
    version='3.0',
    description='MediaWiki SRE Utility Scripts',
    author='MediaWiki SRE - Miraheze',
    author_email='root@root.root',
    url='https://github.com/miraheze/puppet',
    packages=find_packages('.'),
    include_package_data=True,
    install_requires=requirements,
    tests_require=dev_requirements,
    test_suite='tests',
)
