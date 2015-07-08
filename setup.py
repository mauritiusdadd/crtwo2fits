#!/usr/bin/env python2

from distutils.core import setup

setup(name='crtwo2fits',
      version='0.1.0',
      description='',
      author='Maurizio D\'Addona',
      author_email='mauritiusdadd@gmail.com',
      provides=['crtwo2fits'],
      requires=['numpy', 'astropy'],
      packages=['crtwo2fits'],
      package_data={'src': ['data/*', 'data/lang/*']},
      data_files=[('share/licenses/crtwo2fits', ['COPYRIGHT']),
                  ('share/crtwo2fits/', ['conf/crtwo2fits.conf']),
                  ('share/man/man1', ['man/crtwo2fits.man']),
                  ],
      scripts=['scripts/crtwo2fits']
      )
