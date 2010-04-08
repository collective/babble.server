from setuptools import setup, find_packages
import os

version = '0.1a1'

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = (

    read('README.txt')
    + '\n' +
    read('docs', 'CONTRIBUTORS.txt')
    + '\n' +
    read('docs','HISTORY.txt')
    )
    

setup(
    name='babble.server',
    version=version,
    description="A backend babble.server for Zope",
    long_description=long_description,
    # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
    "Programming Language :: Python",
    ],
    keywords='chat zope plone',
    author='JC Brand',
    author_email='jc@opkode.com',
    url='http://svn.plone.org/svn/plone/plone.example',
    license='GPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['babble'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
    ],
    entry_points="""
    """,
    )
