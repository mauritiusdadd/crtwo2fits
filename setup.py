#!/usr/bin/env python
import setuptools

import re
import gzip
import time

BUILD_INFO = {
    'date': time.strftime("%Y-%m"),
    'asctime': time.asctime(),
    'github': ""
}


class ManPagesExtension(setuptools.Extension):

    def __init__(self, name, sources):
        # don't invoke the original build_ext for this special extension
        super().__init__(name, sources=[])

        for fname in sources:
            with open(fname, 'r') as inp_f:
                text = inp_f.read()

            for key, val in BUILD_INFO.items():
                text = re.sub(r'%\('+key+r'\)s', val, text)

            out_f = gzip.open(fname[:-4]+'.gz', 'w')
            out_f.write(text.encode('UTF-8'))
            out_f.close()


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
        ('share/crtwo2fits', ['conf/crtwo2fits.conf']),
    ],
    python_requires=">=3.6",
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3'
    ],
    keywords='cr2 fits astrphotography photo',
    entry_points={
        'console_scripts': [
            'crtwo2fits=crtwo2fits:main',
        ],
    },
    ext_modules=[
        ManPagesExtension('man', [
            'man/crtwo2fits.1.man',
            'man/it/crtwo2fits.1.man',
            'man/crtwo2fits.conf.5.man',
            'man/it/crtwo2fits.conf.5.man'
        ])
    ]
)
