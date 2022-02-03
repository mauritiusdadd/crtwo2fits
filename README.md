[![Build Status](https://app.travis-ci.com/mauritiusdadd/crtwo2fits.svg?branch=master)](https://travis-ci.org/mauritiusdadd/crtwo2fits)

# LEGAL NOTES

Maurizio D'Addona <mauritiusdadd@gmail.com> (C) 2015 - 2022

crtwo2fits is a program for conveertinf CR2 files into FIST images.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see (http://www.gnu.org/licenses/).

# INSTALLATION

## Linux

### Archlinux

To install this package just download the [PKGBUILD](https://aur.archlinux.org/packages/crtwo2fits/) from the AUR and use makepkg.
    
### From sources
If you downloaded a source package, you should use pip to install the required dependencies and then the package itself

    $ pip install -r requirements.txt
    $ pip install .

Finally you should copy the configuration file into /etc:

    # cp /usr/share/crtwo2fits/crtwo2fits.conf /etc

However, it is wisier to make a package compatible with the package manager
of your distribution and use the latter instead of running the installation
script manually.

For list of python dependecies needed by this package see the file requirements.txt

## Windows

Under development

# BUGS AND WISHES

If you find a bug or you just want to suggest a new feature, please
open a issue on github.
