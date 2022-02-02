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
 crtwo2fits.log

 provide custom logging funtions.
"""

import logging


def log(message, level=logging.DEBUG):
    """
    send a text message to the root logger

    Parameters
    ----------
    message : str
        a text message to be logged. If the message
        contains more than one line, then each line
        is logged separately

    level : int, optional
        the logging level of the message. Default is
        logging.DEBUG (10)

    Returns
    -------
    None

    Examples
    --------
    >>> crtwo2fits.log("Decoding process started", logging.INFO)

    """
    logger = logging.getLogger()
    for each_message in str(message).splitlines():
        if logger is not None:
            logger.log(level, each_message)
