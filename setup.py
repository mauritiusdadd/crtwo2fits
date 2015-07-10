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
      package_data={'crtwo2fits': ['data/*', 'data/lang/*']},
      data_files=[
          ('share/licenses/crtwo2fits', ['COPYRIGHT']),
          ('etc', ['conf/crtwo2fits.conf']),
          ('share/man/man1', ['man/crtwo2fits.1.gz']),
          ('share/man/man5', ['man/crtwo2fits.conf.5.gz']),
          ('share/man/it/man1', ['man/it/crtwo2fits.1.gz']),
          ('share/man/it/man5', ['man/it/crtwo2fits.conf.5.gz']),
          ('share/crtwo2fits', ['lang/crtwo2fits.po.skel']),
          ('share/crtwo2fits/it/LC_MESSAGES',
           ['lang/it/LC_MESSAGES/crtwo2fits.po',
            'lang/it/LC_MESSAGES/crtwo2fits.mo'])
      ],
      scripts=['scripts/crtwo2fits']
      )
