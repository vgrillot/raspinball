"""Independant platform implementation for MPF based on Raspberry PI and Arduino."""

from setuptools import setup

setup(

    name='rasppinball_platform',
    version='0.1',
    description='Mission Pinball Framework External Platform',
    long_description='''Personnal implementation of MPF platform for Raspberry and Arduino''',

    url='https://thelegomoviepinball.wordpress.com/',
    author='Vincent GRILLOT',
    author_email='grivin@gmail.com',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Natural Language :: French',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Topic :: Artistic Software',
        'Topic :: Games/Entertainment :: Arcade'

    ],

    keywords='pinball',

    include_package_data=True,

    # MANIFEST.in picks up the rest
    packages=['rasppinball_platform'],

    install_requires=['mpf'],

    tests_require=[],

    entry_points='''
    [mpf.platforms]
    rasppinball_platform=rasppinball_platform.rasppinball:RasppinballHardwarePlatform
    '''
)
