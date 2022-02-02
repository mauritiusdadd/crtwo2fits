#!/usr/bin/env python
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='crtwo2fits',
    version='0.2.0',
    author='Maurizio D\'Addona',
    author_email='mauritiusdadd@gmail.com',
    url='https://github.com/mauritiusdadd/crtwo2fits',
    description='',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        'crtwo2fits': [
        'data/lang/*.skel',
        'data/lang/it/LC_MESSAGES/*.po',
        'data/lang/it/LC_MESSAGES/*.mo',
        ]
    },
    data_files=[
        ('share/licenses/crtwo2fits', ['COPYRIGHT']),
        ('share/man/man1', ['man/crtwo2fits.1.gz']),
        ('share/man/man5', ['man/crtwo2fits.conf.5.gz']),
        ('share/man/it/man1', ['man/it/crtwo2fits.1.gz']),
        ('share/man/it/man5', ['man/it/crtwo2fits.conf.5.gz']),
        ('share/crtwo2fits', [
                'conf/crtwo2fits.conf',
                'lang/crtwo2fits.po.skel'
            ]
        ),
        ('share/crtwo2fits/it/LC_MESSAGES',
        ['lang/it/LC_MESSAGES/crtwo2fits.po',
        'lang/it/LC_MESSAGES/crtwo2fits.mo'])
    ],
    scripts=['scripts/crtwo2fits'],
    python_requires=">=3.6",
)
