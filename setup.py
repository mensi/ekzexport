from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

setup(
    name='ekzexport',
    description='CLI and data exporter for the myEKZ customer portal.',
    long_description=readme,
    long_description_content_type="text/markdown",
    author='Manuel Stocker',
    author_email='mensi@mensi.ch',
    url='https://github.com/mensi/ekzexport',
    license='Apache-2.0',
    version='0.1.1',
    packages=['ekzexport', 'ekzexport.exporters'],
    package_data={'': ['LICENSE']},
    package_dir={'': 'src'},
    install_requires=[
        'requests',
        'click',
        'beautifulsoup4',
        'rich',
        'platformdirs',
        'tzdata',
    ],
    extras_require={
        'influx': ['influxdb-client'],
    },
    tests_require=[
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'ekzexport = ekzexport.cli:main',
        ],
    },
    classifiers=[
            "License :: OSI Approved :: Apache Software License",
            "Natural Language :: English",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3 :: Only",
        ],
)
