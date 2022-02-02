# crtwo2fits is a program to convert CR2 files into FITS images
# Copyright (C) 2015-2022  Maurizio D'Addona <mauritiusdadd@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
 crtwo2fits

 crtwo2fits is a native python module which provides the basic classes
 and functions to convert CR2 files into FITS images.

 Use the help command on each submodule to access its documentation.
 The following submodules are available:

    cr2 - provides the CR2Image classes and FITS conversion functions.
    log - provide custom logging funtions.

"""

from . import log
from . import cr2

__all__ = ['cr2', 'log']
