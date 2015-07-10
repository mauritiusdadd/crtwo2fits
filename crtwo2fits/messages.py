# crtwo2fits is a program to convert CR2 files into FITS images
# Copyright (C) 2015  Maurizio D'Addona <mauritiusdadd@gmail.com>
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
crtwo2fits.messages

English messages
"""

ERR_NO_ASTROPY = (
  "\nCan't import the python package 'astropy'.\n"
  "Please install the package 'astropy'!\n"
  "You can find it at http://www.astropy.org/\n"
)

ERR_NOT_PGM = "Not a raw PGM data"

DBG_IMG_WID = "Image width: {}"

DBG_IMG_HEI = "Image height: {}"

DBG_IMG_DTP = "Image dtype: {}"

DBG_PGM_RAW_FOUND = "Found raw PGM data"

DBG_PGM_TXT_FOUND = "Found plain text PGM data"

DBG_DECODER_NATIVE = "Using native decoder"

DBG_DECODER_EXT = "Using external decoder"

DBG_IMAGE_SIZE = "Image size: {1}x{0}"

DBG_OUTPUT_SIZE = "Output size: {1}x{0}"

DBG_SENSOR_SIZE = "Sensor size: {1}x{0}"

ERR_EXT_DECODER = "An error has occured in {}: '{}'"

ERR_MARKER_EOI = "EOI marker does not correspond to end of image"

ERR_MARKER_SOI = "SOI marker does not correspond to start of image"

ERR_PGM_INVALID = "corrupted or invalid PGM data"

ERR_PGM_UNSUPPORTED = "Unsupported PGM data format"

ERR_UNKNOWN_ENDIAN = "unknown endian format"

ERR_NOT_CR2 = "not a CR2 image file"

ERR_SMALL_RAW = (
  "Oops, full frame image is smaller "
  "than than requestes size, cannot proced!"
)

WRN_CORRUPTED_CR2 = "Warning: probably corrupted data!"

WRN_NO_DECODER = (
  "External decoder not found: "
  "only native decoder is available"
)
