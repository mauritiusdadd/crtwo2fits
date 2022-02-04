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
#
# NOTE: This module is based on the cr2plugin module of lxnstack
#       but has evolved as a standalone module to directly decode
#       CR2 files

"""
 crtwo2fits.cr2

 provides the class CR2Image and FITS conversion functions.

 The information used to wirte this module were taken form:

 (1) Canon (TM) CR2 specifications:
     http://lclevy.free.fr/cr2/

 (2) Lossless Jpeg and Huffman decoding:
     http://www.impulseadventure.com/photo/jpeg-huffman-coding.html

 (3) Lossless Jpeg information
     http://www.digitalpreservation.gov/formats/fdd/fdd000334.shtml

 (4) Dave Coffin's raw photo decoder (only for predictors values)
     http://www.cybercom.net/~dcoffin/dcraw/
"""

import os
import re
import struct
import gettext
import logging
import logging.handlers
import subprocess
import numpy as np

from . import log
from . import messages as msg

DATADIR = os.path.join(os.path.dirname(__file__), 'data')
LOCALEDIR = os.path.join(DATADIR, 'lang')

tr = gettext.translation(
    'crtwo2fits',
    os.path.abspath(LOCALEDIR),
    fallback=True
)
tr = tr.gettext

try:
    import astropy.io.fits as pyfits
except ImportError:
    print(tr(msg.ERR_NO_ASTROPY))

EXTENSION = {'.cr2': 'CR2'}

PGM_SEPS = b' \t\r\n'

IMAGE_WIDTH = 256
IMAGE_LENGTH = 257
IMAGE_DESCRIPTION = 270
MAKE = 271
MODEL = 272
STRIP_OFFSET = 273
STRIP_BYTES_COUNT = 279
EXIF = 34665
CR2_SLICE = 50752
EXPOSURE_TIME = 33434
MAKERNOTE = 37500

CAMERA_SETTINGS = 0x0001
FOCUS_INFO = 0x0002
IMAGE_TYPE = 0x0006
SENSOR_INFO = 0x00e0
COLOR_BALANCE = 0x4001
BLACK_LEVEL = 0x4008
VIGNETTING_CORRECTION = 0x4015

# Huffman Table marker
DHT_MARKER = b'\xff\xc4'

# Start Of Frame marker
SOF_MARKER = b'\xff\xc3'

# Start Of Scan marker
SOS_MARKER = b'\xff\xda'

# Start Of Image marker
SOI_MARKER = b'\xff\xd8'

# End Of Image marker
EOI_MARKER = b'\xff\xd9'

MAX_HUFFMAN_BITS = 16
MIN_BUFFER_LEN = 2*MAX_HUFFMAN_BITS

DECODESTRING = '>'+'Q'*16  # 16 * 8 bytes
TOKENLEN = struct.calcsize(DECODESTRING)
bittokenlen = TOKENLEN*8

STD_FITS_HEADER = [
    ('SWCREATE', "crtwo2fits"),
    ('BITPIX', 16),
    ('NAXIS', 2)
]

EXIF_TAGS = {}


def getFitsStdHeader():
    """
    Return a basic FIST header based on STD_FITS_HEADER

    Parameters
    ----------
    None

    Returns
    -------
    head : astropy.io.fits.Header
        a fits header object

    Examples
    --------
    >>> import crtwo2fits.cr2 as cr2
    >>> header = cr2.getFitsStdHeader()
    >>> print(repr(h))
    SWCREATE= 'crtwo2fits'
    BITPIX  =                   16
    NAXIS   =                    2
    """
    try:
        return pyfits.header.Header(STD_FITS_HEADER)
    except Exception:
        # old pyfits method!
        head = pyfits.Header()
        for line in STD_FITS_HEADER:
            head.update(line[0], line[1])
        return head


def ba2bs2(b):
    """
    Helper function for Huffman decoder: converts
    a bytes/bytearray object to a bynary bitstring
    where each byte is mapped to is 8-bit representation

    Parameters
    ----------
    b : byte or bytearray
        byte sequence to convert

    Returns
    -------
    s : str
        bistring representation of b

    See also
    --------
    ba2bs

    Examples
    --------
    >>> import crtwo2fits.cr2 as cr2
    >>> cr2.ba2bs2(b'\x05')
    '00000101'
    >>> cr2.ba2bs(b'Hello')
    '0100100001100101011011000110110001101111'
    """
    m = map('{0:08b}'.format, b)
    s = ''.join(m)
    return s


def ba2bs(b):
    """
    Helper function for Huffman decoder: similar to
    ba2bs2, but needs packaed data. The coding structure
    is defined by the constant DECODESTRING.

    See also
    --------
    ba2bs2
    """
    d = struct.unpack(DECODESTRING, b)
    m = map('{0:064b}'.format, d)
    s = ''.join(m)
    return s


def _reconstructData(byte_order, *bytesdata):
    """
    Helper function for Huffman decoder
    """
    result = 0

    if byte_order == b'II':
        for b in range(len(bytesdata)):
            data = bytesdata[b]
            if type(data) == str:
                data = ord(data)
            offs = b * 8
            result += data << offs
    else:
        for b in range(len(bytesdata)):
            data = bytesdata[-b]
            if type(data) == str:
                data = ord(data)
            offs = b * 8
            result += data << offs
    return result


def _reconstructDataFromString(byte_order, bytesdata):
    """
    Helper function for Huffman decoder
    """
    result = 0
    if byte_order == b'II':
        for b in range(len(bytesdata)):
            data = bytesdata[b]
            if type(data) == str:
                data = ord(data)
            offs = b * 8
            result += data << offs
    else:
        for b in range(len(bytesdata)):
            data = bytesdata[b]
            if type(data) == str:
                data = ord(data)
            offs = (len(bytesdata) - b - 1) * 8
            result += data << offs
    return result


def _getTypeSize(ind):
    """
    Helper function for EXIF table reader

    Return the size in byte of the specified type

    Parameters
    ----------
    ind : int
        The type id. The following values are allowed
         id |      type     | size
        ----|---------------|------
          1 | byte          |  1
          2 | ascii         | nan
          3 | short         |  2
          4 | long          |  4
          5 | rational      |  8
          6 | singed byte   |  1
          7 | undefined     | nan
          8 | signed short  |  2
          9 | signed long   |  4
         10 | sig. rational |  8
         11 | float         |  4
         12 | double        |  8

    Returns
    -------
    out : int
        returns the size in bytes of the specified type.
        For ascii type it returns -1
        For undefined type it returns -2
        For any id that does not match any known type, it
        returns None

    See also
    --------
    _getExifValue

    Examples
    --------
    >>> import crtwo2fits.cr2 as cr2
    >>> cr2._getTypeSize(0)

    >>> cr2._getTypeSize(1)
    1
    >>> cr2._getTypeSize(2)
    -1
    >>> cr2._getTypeSize(7)
    -2
    """
    if ind == 1:     # byte
        return 1
    elif ind == 2:   # ascii
        return -1
    elif ind == 3:   # short
        return 2
    elif ind == 4:   # long
        return 4
    elif ind == 5:   # rational
        return 8
    elif ind == 6:   # signed byte
        return 1
    elif ind == 7:   # undefined
        return -2
    elif ind == 8:   # signed short
        return 2
    elif ind == 9:   # signed long
        return 4
    elif ind == 10:  # signed rational
        return 8
    elif ind == 11:  # float
        return 4
    elif ind == 12:  # double
        return 8


def _getExifValue(data, data_type):
    """
    Converts the raw EXIF data into the correspondig type

    Parameters
    ----------
    data : byte or bytearray
        the raw data

    data_type : int
        the type id

    Returns
    -------
    data : variable type
        the type is determinated using the data type id
        according to the following table

         id |      type
        ----|---------------
          1 | numpy.ubyte
          2 | str
          3 | numpy.uint16
          4 | numpy.uint32
          5 | 0 or "nan" or
            | (uint32, uint32)
          6 | numpy.byte
          7 | type(data)
          8 | numpy.int16
          9 | numpy.int32
         10 | 0 or "nan" or
            | (int32, int32)
         11 | numpy.float32
         12 | numpy.float64

    See also
    --------
    _getTypeSize

    Examples
    --------
    >>> import crtwo2fits.cr2 as cr2
    >>> cr2._getExifValue(b'12', 1)
    12
    >>> cr2._getExifValue(b'260', 1)
    4
    >>> cr2._getExifValue(b'129', 6)
    -127
    >>> cr2._getExifValue(b'129', 4)
    129
    >>> i = (9 << 32) + 4
    >>> val = cr2._getExifValue(i, 5)
    (4, 9)
    """
    if data_type == 1:
        return np.ubyte(data)
    elif data_type == 2:
        chars = bytes(data).replace(b'\x00', b'')
        try:
            return chars.decode('ascii')
        except UnicodeDecodeError:
            try:
                return chars.decode('UTF-8')
            except UnicodeDecodeError:
                return str(data)
    elif data_type == 3:
        return np.uint16(data)
    elif data_type == 4:
        return np.uint32(data)
    elif data_type == 5:
        n = np.uint32(0xffffffff & data)
        d = np.uint32(((0xffffffff << 32) & data) >> 32)
        if n == 0:
            return 0
        elif d == 0:
            return "nan"
        else:
            return (n, d)
    elif data_type == 6:
        return np.byte(data)
    elif data_type == 7:
        return data
    elif data_type == 8:
        return np.int16(data)
    elif data_type == 9:
        return np.int32(data)
    elif data_type == 10:
        n = np.int32(0xffffffff & data)
        d = np.int32(((0xffffffff << 32) & data) >> 32)
        if n == 0:
            return 0
        elif d == 0:
            return "nan"
        else:
            return (n, d)
    elif data_type == 11:
        return np.float32(data)
    elif data_type == 12:
        return np.float64(data)
    else:
        return data


def pgm2numpy(data, byteorder='>'):
    """
    Convert PGM data to numpy array

    Parameters
    ----------

    data : bytes
        the PGM raw (binary) or plain text data

    byteorder : str, default='>'
        the byte order of binary data. Has effect only
        if binary PGM data is passed to the function.

        Allowed values are

        '=' - native
        '<' - little endian
        '>' - big endian
        '|' - not applicable

        See numpy.dtype.byteorder for more information.

    Examples
    --------
    >>> import crtwo2fits.cr2 as cr2
    >>> PGM = b'P2 3 3 10 1 2 3 4 5 6 7 8 9'
    >>> n = cr2.pgm2numpy(PGM)
    >>> n.shape
    (3, 3)
    >>> n
    array([[ 1.,  2.,  3.],
           [ 4.,  5.,  6.],
           [ 7.,  8.,  9.]])
    """

    try:
        field = re.search(
            rb"^P([25])(?:\s*#.*)*\s"
            rb"(\d+)(?:\s*#.*)*\s"
            rb"(\d+)(?:\s*#.*)*\s"
            rb"(\d+)(?:\s*#.*)*\s"
            rb"((?:.*\s*)*)",
            data
        ).groups()
    except AttributeError:
        log.log(tr(msg.ERR_NOT_PGM), logging.ERROR)
        return None
    else:
        pid = int(field[0])
        width = int(field[1])
        height = int(field[2])
        maxval = int(field[3])
        lenght = width*height
        image_data = field[4]

        if maxval > 255:
            data_type = byteorder+'u2'
        else:
            data_type = 'u1'

        log.log(tr(msg.DBG_IMG_WID.format(width)),
                logging.DEBUG)
        log.log(tr(msg.DBG_IMG_HEI.format(height)),
                logging.DEBUG)
        log.log(tr(msg.DBG_IMG_DTP.format(data_type)),
                logging.DEBUG)

    if pid == 5:

        # Raw (bynary) pgm data
        log.log(tr(msg.DBG_PGM_RAW_FOUND),
                logging.DEBUG)
        n = np.frombuffer(image_data,
                          dtype=data_type,
                          count=lenght)
    elif pid == 2:

        # plain text pgm data
        # NOTE: comments extends until end of line!
        log.log(tr(msg.DBG_PGM_TXT_FOUND),
                logging.DEBUG)
        value = re.findall(rb"(\d+)(?:\s*#.*)*\s*", image_data)

        if len(value) != lenght:
            log.log(tr(msg.ERR_PGM_INVALID),
                    logging.ERROR)
            return None

        n = np.empty((lenght))
        for i in range(lenght):
            n[i] = int(value[i])
    else:
        log.log(tr(msg.ERR_PGM_UNSUPPORTED),
                logging.ERROR)
        return None

    return n.reshape((height, width))


def getPredictorValue(psv, px_left, px_top, px_topleft):
    """
     Return the predictor value for a pixel P from
     its neighbours according to the psv value.

                  COLOR COMPONENT X

             ... +--------+--------+ ...
                 |        |        |
                 |top_left|  top   |
                 |        |        |
             ... +--------+--------+ ...
                 |        |        |
                 |  left  |   P    |
                 |        |        |
             ... +--------+--------+ ...

    Parameters
    ----------

    psv : int
        the predictor selection value

    px_left : int
        the value of the left neighbour pixel

    px_top: int
        the value of the top neighbour pixel

    px_topleft : int
        the value of the top-left neighbour pixel

    Returns
    -------

    predictor : int
        From the (3) Lossless JPEG specifications
        and (4) dcraw source code the following
        predictors for a pixel P can be found:

        ScanTable.psv = 1 --> predictor = left pixel
        ScanTable.psv = 2 --> predictor = top pixel
        ScanTable.psv = 3 --> predictor = top_left pixel
        ScanTable.psv = 4 --> predictor = left + top - top_left
        ScanTable.psv = 5 --> predictor = left + ((top - top_left) >> 1)
        ScanTable.psv = 6 --> predictor = top + ((left - top_left) >> 1)
        ScanTable.psv = 7 --> predictor = (top + left)>>1

        Therefore, the returned predictor value is
        computed as follow:

             psv |        predictor
            -----|------------------------
              0  | 0
              1  | px_left
              2  | px_top
              3  | px_topleft
              4  | px_left + px_top - px_topleft
              5  | px_left + ((px_top - px_topleft) >> 1)
              6  | px_top + ((px_left - px_topleft) >> 1)
              7  | (px_top - px_left) >> 1
             ... | 0
    """
    if psv == 1:
        pred = px_left
    elif psv == 2:
        pred = px_top
    elif psv == 3:
        pred = px_topleft
    elif psv == 4:
        pred = px_left + px_top - px_topleft
    elif psv == 5:
        pred = px_left + ((px_top - px_topleft) >> 1)
    elif psv == 6:
        pred = px_top + ((px_left - px_topleft) >> 1)
    elif psv == 7:
        pred = (px_top - px_left) >> 1
    else:
        pred = 0

    return pred


class Sensor(object):
    """
    crtwo2fits.cr2.Sensor

    This class holds the properties of the camera sensor as
    specified by the MAKERNOTE table inside the CR2 file.


                            SENSOR
      +---------------------------------------------+
      |                            TOP BORDER |  '  | |
      |      _________________________________v  '  | |
      |  L  |                                 |  '  | |
      |  E  |                                 |  '  | |
      |  F  |                                 | B'B | H
      |  T  |                                 | O'O | E
      |     |                                 | T'R | I
      |  B  |                                 | T'D | G
      |  O  |                                 | O'E | H
      |  R  |                                 | M'R | T
      |  D  |                                 |  '  | |
      |  E  |                                 |  '  | |
      |  R  |                                 |  '  | |
      |- - >|_________________________________|..v  | |
      |                                       '     | |
      |- - - - - - - RIGHT BORDER- - - - - - >'     | |
      +---------------------------------------------+ v
      - - - - - - - - - - WIDTH - - - - - - - - - ->

    Parameters
    ----------
    data : tuple of ints
        a tuple containing the values of the class attributes

    Attributes
    ----------
    width : int
        the width of the sensor in pixels

    height : int
        the height of the sensor in pixels

    left_border : int
        the left margin of the actual image

    top_border : int
        the top margin of the actual image

    right_border : int
        the right margin of the actual image

    bottom_border : int
        the bottom margin of the actual image

    black_mask_left_border : int
        the left margin of the area used to
        compute the black level

    black_mask_top_border : int
        the top margin of the area used to
        compute the black level

    black_mask_right_border : int
        the right margin of the area used to
        compute the black level

    black_mask_bottom_border : int
        the bottom margin of the area used to
        compute the black level
    """

    def __init_tr(self, data=(0, 0, 0, 0, 0, 0, 0, 0,
                              0, 0, 0, 0, 0, 0, 0, 0, 0)):
        self.width = data[1]
        self.height = data[2]
        self.left_border = data[5]
        self.top_border = data[6]
        self.right_border = data[7]
        self.bottom_border = data[8]
        self.black_mask_left_border = data[9]
        self.black_mask_top_border = data[10]
        self.black_mask_right_border = data[11]
        self.black_mask_bottom_border = data[12]

    def __str_tr(self):
        s = 'Sensor Width : ' + str(self.width) + '\n'
        s += 'Sensor Height : ' + str(self.height) + '\n'
        s += 'Border Top : ' + str(self.top_border) + '\n'
        s += 'Border Bottom : ' + str(self.bottom_border) + '\n'
        s += 'Border Left : ' + str(self.left_border) + '\n'
        s += 'Border Right : ' + str(self.right_border) + '\n'
        s += 'Black Mask Top : ' + str(self.black_mask_top_border) + '\n'
        s += 'Black Mask Bottom : ' + str(self.black_mask_bottom_border) + '\n'
        s += 'Black Mask Left : ' + str(self.black_mask_left_border) + '\n'
        s += 'Black Mask Right : ' + str(self.black_mask_right_border) + '\n'

        return s


class HuffmanTable(object):

    """
    crtwo2fits.cr2.HuffmanTable

    This class holds the information of the Huffman table

    Parameters
    ----------
    data : bytes
        raw data from CR2 file
    """

    def __init_tr(self, data=None):

        self.codes = {}

        # bitmasks for faster computation
        self.masks = []
        for i in range(MAX_HUFFMAN_BITS):
            self.masks.append((1 << i) - 1)

        if (data is not None):

            if data[0:2] != DHT_MARKER:
                raise SyntaxError("Invalid Huffman Talbe")

            offset = 4
            while offset < len(data):

                info = data[offset]
                index = info & 0b00000111
                type = info & 0b00010000
                symbols = {0: []}
                count = 0

                if (info & 0b11110000) != 0:
                    raise SyntaxError("Invalid Huffman Talbe")

                for i in range(MAX_HUFFMAN_BITS):
                    current = data[offset+1+i]
                    symbols[i+1] = [None] * current

                for i in range(MAX_HUFFMAN_BITS):
                    for j in range(len(symbols[i+1])):
                        current = data[offset+0x11+count]
                        symbols[i+1][j] = current
                        count += 1
                offset = offset + 0x11 + count

                self.codes[index, type] = self.generateCodes(symbols)

    def __repr_tr(self):

        s = "\n"
        s += "-----------------------------\n"
        s += "|       Huffman Table       |\n"
        s += "-----------------------------\n"

        keyslst = sorted(self.codes.keys())
        for kk in keyslst:
            s += "|  Index |        0"+str(kk[0])+"        |\n"
            if kk[1] == 0:
                s += "|  Type  |        DC        |\n"
            else:
                s += "|  Type  |        AC        |\n"
            s += "-----------------------------\n"
            s += "|       BITS       |  CODE  |\n"
            s += "-----------------------------\n"

            keyslst2 = sorted(self.codes[kk].keys())
            for i in keyslst2:
                codes = self.codes[kk][i]
                s += "| {0:s}  |  0x{1:02x}  |\n".format(i.rjust(15), codes)
            s += "-----------------------------\n"
        return s

    def generateCodes(self, sym):
        """
        Generate the Huffman table structure
        """

        branches = [['']]
        leafs = []
        current_count = 0
        row = 0
        codes = {}

        totalcodes = 0
        for cod in sym.values():
            totalcodes += len(cod)

        # finding last non empty row
        last_non_null = 0
        for i in sym.keys():
            if len(sym[i]) != 0:
                last_non_null = i

        while (len(leafs) < totalcodes) and (row <= last_non_null):

            lst = []
            current_count = 0
            current_max = len(sym[row+1])
            for p in branches[row]:
                for j in range(2):
                    i = p + str(j)
                    if current_count < current_max:
                        leafs.append(i)
                        codes[i] = sym[row+1][current_count]
                        current_count += 1
                    else:
                        lst.append(i)
            row += 1
            branches.append(lst)

        del branches
        del leafs
        return codes


class FrameTable(object):

    """
    crtwo2fits.cr2.FrameTable

    This class holds the information of the FrameTable
    from the lossless JPEG data inside the CR2 file

    Parameters
    ----------
    data : bytes
        raw data from CR2 file
    """

    def __init_tr(self, data):

        self.bits = data[4]
        self.height = _reconstructDataFromString(b'MM', data[5:7])
        self.width = _reconstructDataFromString(b'MM', data[7:9])
        self.components = data[9]
        self.componentsPropetries = {}

        for i in range(self.components):
            index = data[10+3*i]
            hv = data[10+3*i+1]
            quant = data[10+3*i+2]
            pdic = {'index': index,
                    'h': (hv & 0b11110000) >> 4,
                    'v': (hv & 0b00001111),
                    'qunatization_table': quant
                    }
            self.componentsPropetries[i] = pdic

    def __repr_tr(self):
        s = '\n'
        s += "-----------------------------\n"
        s += "|        Frame Table        |\n"
        s += "-----------------------------\n"
        s += "|                            \n"
        s += "| bits : " + str(self.bits) + "\n"
        s += "| width : " + str(self.width) + "\n"
        s += "| height : " + str(self.height) + "\n"
        s += "| components # : " + str(self.components) + "\n"
        s += "-----------------------------\n"
        s += "|         Components        |\n"
        s += "-----------------------------\n"
        s1 = str(self.componentsPropetries)
        s1 = s1.replace(': {', ' -> ')
        s1 = s1.replace('{', '|')
        s1 = s1.replace('},', '\n|')
        s1 = s1.replace('}', '\n')
        s1 = s1.replace(' ', '')
        s1 = s1.replace(',', '; ')
        s1 = s1.replace(':', ' = ')
        s += s1
        s += "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n"
        return s


class ScanTable(object):
    """
    crtwo2fits.cr2.ScanTable

    This class holds the information of the ScanTable
    from the lossless JPEG data inside the CR2 file

    Parameters
    ----------
    data : bytes
        raw data from CR2 file
    """

    def __init_tr(self, data):

        self.components = data[4]
        self.componentsPropetries = {}
        self.psv = data[4+2*self.components+1]
        self.ssending = data[4+2*self.components+2]
        self.succ_approx = data[4+2*self.components+3]

        for i in range(self.components):
            index = data[5+2*i]
            da = data[5+2*i+1]
            pdic = {'index': index,
                    'DC': (da & 0b1111000) >> 4,
                    'AC': (da & 0b00001111),
                    }
            self.componentsPropetries[i] = pdic

    def __repr_tr(self):
        s = '\n'
        s += "-----------------------------\n"
        s += "|         Scan Table        |\n"
        s += "-----------------------------\n"
        s += "|                            \n"
        s += "| components # : " + str(self.components) + "\n"
        s += "| P.S.V.: " + str(self.psv) + "\n"
        s += "| SS ending: " + str(self.ssending) + "\n"
        s += "| SA : " + str(self.succ_approx) + "\n"
        s += "-----------------------------\n"
        s += "|         Components        |\n"
        s += "-----------------------------\n"
        s1 = str(self.componentsPropetries)
        s1 = s1.replace(': {', ' -> ')
        s1 = s1.replace('{', '|')
        s1 = s1.replace('},', '\n|')
        s1 = s1.replace('}', '\n')
        s1 = s1.replace(' ', '')
        s1 = s1.replace(',', '; ')
        s1 = s1.replace(':', ' = ')
        s += s1
        s += "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n"
        return s


class CR2Image(object):

    """
    crtwo2fits.cr2.CR2Image

    This object handles a CR2 file

    Parameters
    ----------
    fname : str, optional
        full path of the CR2 file. If this parameter is
        passed, the file will be opened in the object
        initialization. If the file cannot be opened an
        exception is raised.

    ext_decoder : str, optional
        the full path of an external decoder executable.
        The decore must return the full-frame size image
        as PGM data (either as binary data or plain text)
        on the the standard output.

    decoder_fmt_str : str, optional
        the command used to invoke the external decoder.
        the keywords {exec} and {file} are replaced
        by self.ext_decoder and self.filename respectively

    Attributes
    ----------
    filename : str
        the name of the currently opened CR2 file

    fp : file object
        the file object for the currently opened file

    version : float
        the version of the CR2 file format. Should
        always be 2.0

    isOpened : bool
        indicates if the CR2 file is currently opened

    """

    format = "CR2"
    format_description = "Canon Raw format version 2"

    def __init_tr(self, fname=None, ext_decoder=None, decoder_fmt_str=""):

        self.version = 0
        self.isOpened = False
        self.decoder_exec = ext_decoder
        self.decoder_fmt = decoder_fmt_str

        if not self.hasExternalDecoder():
            log.log(tr(msg.WRN_NO_DECODER),
                    logging.WARNING)

        if fname is not None:
            self.filename = fname
            self.fp = open(self.filename, 'rb')
            self.open()

    def hasExternalDecoder(self):
        if self.decoder_exec is None:
            return False
        else:
            return os.path.isfile(self.decoder_exec)

    def __del_tr(self):
        self.close()

    def getImageBorders(self):
        """
        The camera has a sensor with a Bayer matrix, so border values
        *must* be multiple of 2 and cropped image *must* be within
        the MAKERENOT borders

                                    SENSOR
              +---------------------------------------------+
              |                            TOP BORDER |  '  | |
              |      _________________________________v  '  | S
              |  L  |    ^                            |  '  | E
              |  E  |    |                            |  '  | N
              |  F  |    H                            | B'B | S
              |  T  |    E                            | O'O | O
              |     |    I                            | T'R | R
              |  B  |    G          IMAGE             | T'D |
              |  O  |    H                            | O'E | H
              |  R  |    T                            | M'R | E
              |  D  |    |                            |  '  | I
              |  E  |<---+----------WIDTH------------>|  '  | G
              |  R  |    |                            |  '  | H
              |- - >|____v____________________________|..v  | T
              |                                       '     | |
              |- - - - - - - RIGHT BORDER- - - - - - >'     | |
              +---------------------------------------------+ v
              - - - - - - - - -SENSOR WIDTH- - - - - - - - >

        Paramenters
        -----------
        None

        Returns
        -------

        borders : tuple of four ints
            The image margins relative to the top-left most
            pixel of the sensor, in the format of
            (left, bottom, right, top)

        """
        bbord = self.Sensor.bottom_border - (self.Sensor.bottom_border % 2)
        tbord = self.Sensor.top_border + (self.Sensor.top_border % 2)
        lbord = self.Sensor.left_border + (self.Sensor.left_border % 2)
        rbord = self.Sensor.right_border - (self.Sensor.right_border % 2)
        return (lbord, bbord, rbord, tbord)

    def load(self, fname=None, ifd=3, full_frame=False, native_decoder=False):
        """
        Load an image data from the CR2 file. If the file is closed
        this function will open it too.

        Parameters
        ----------
            fname : str, optional
                The name of the file to open. If this parameter is
                not passed, then the current CR2 file is used.

            ifd : int, optional
                The indec of the image frame index to read.
                If this parameted is not passed then the third
                frame (the RAW image) is opened.

                Currently the following value are allowed:

                 ifd |   frame   |       status
                -----|-----------|----------------------
                  1  | RGB JPEG  | not implemented yet
                  3  | RAW IMAGE | native & ext. decoder

            full_frame : bool, optional
                If this parameter is True, then the MAKERNOTE borders
                are ignored and the full-sensor image is returned.

                If the value of this parameter is not specified,
                False is assumed by default

            native_decoder : bool
                If this parameter is True, then the native decoder
                is used instead of the external one. The default
                value is False.

        Returns
        -------
            image : numpy.ndarray or None
                The functions returns a numpy.ndarray representing
                the decompressed image  or None if the decoding
                process failed.

                The array has the shape (image height, image width)
        """

        if (not self.isOpened):
            if fname is None:
                raise SyntaxError("unknown file name")
            else:
                self.filename = fname
                self.open()
        if ifd == 3:
            if native_decoder or not self.hasExternalDecoder():
                uncropped = self.decodeRawImage()
            else:
                uncropped = self.decodeExternalDecoder()

            if uncropped is None:
                return None

            log.log(tr(msg.DBG_SENSOR_SIZE.format(*uncropped.shape)),
                    logging.DEBUG)

            if full_frame:
                log.log(tr(msg.DBG_OUTPUT_SIZE.format(*uncropped.shape)),
                        logging.DEBUG)
                return uncropped

            border = self.getImageBorders()

            bbord = border[1]
            tbord = border[3]
            lbord = border[0]
            rbord = border[2]

            try:
                image = uncropped[tbord:bbord, lbord:rbord].copy()
                log.log(tr(msg.DBG_IMAGE_SIZE.format(*image.shape)),
                        logging.DEBUG)
            except IndexError:
                log.log(tr(msg.ERR_SMALL_RAW),
                        logging.ERROR)
                image = None

            del uncropped

        elif ifd == 1:
            image = self.extractEmbeddedJpeg()

        if image is not None:
            pass

        return image

    def open(self):
        """
        Open the current CR2 file and extracts the
        basic information needed for the decoding process.

        If the file is opened successfully the attribute
        self.isOpened is set to True
        """

        header = self.fp.read(0x0f)

        byteorder = header[0:2]
        self.byteorder = byteorder

        # mode setting
        if byteorder == b'II':
            self.mode = "L;16"
        elif byteorder == b'MM':
            self.mode = "L;16B"
        else:
            raise SyntaxError(tr(msg.ERR_UNKNOWN_ENDIAN))

        if (header[2:3] != b'*') or (header[8:10] != b'CR'):
            raise SyntaxError(tr(msg.ERR_NOT_CR2))

        major_version = str(header[0x0a])  # should be 2
        minor_version = str(header[0x0b])  # should be 0

        # and this should be 2.0
        self.version = float(major_version + '.' + minor_version)

        ifd0_offset = _reconstructDataFromString(byteorder, header[4:8])
        ifd3_offset = _reconstructDataFromString(byteorder, header[12:16])

        # the IFD0 for sensor information
        self.IFD0 = self._readIfd(byteorder, ifd0_offset)

        if (EXIF not in self.IFD0.keys()):
            raise SyntaxError(tr(msg.ERR_NOT_CR2))

        exif_offset = self.IFD0[EXIF]

        self.EXIF = self._readIfd(byteorder, exif_offset)

        if (MAKERNOTE not in self.EXIF.keys()):
            raise SyntaxError(tr(msg.ERR_NOT_CR2))

        self.MAKERNOTES = self._readIfd(byteorder, self.EXIF[MAKERNOTE][2])

        self.Sensor = Sensor(self.MAKERNOTES[SENSOR_INFO])

        border = self.getImageBorders()

        bbord = border[1]
        tbord = border[3]
        lbord = border[0]
        rbord = border[2]

        self.size = (rbord - lbord, bbord - tbord)

        # the RAW IFD
        self.IFD3 = self._readIfd(byteorder, ifd3_offset)

        if (CR2_SLICE not in self.IFD3.keys()):
            self.CR2_SLICES = (self.IFD3[STRIP_OFFSET],
                               0,
                               self.IFD3[STRIP_BYTES_COUNT],
                               -1,
                               0)
        else:
            self.CR2_SLICES = (self.IFD3[STRIP_OFFSET],
                               self.IFD3[CR2_SLICE][0],
                               self.IFD3[STRIP_BYTES_COUNT],
                               self.IFD3[CR2_SLICE][1],
                               self.IFD3[CR2_SLICE][2])

        self.isOpened = True

    def close(self):
        """
        Close the currently opened CR2 file and set
        the attribute self.isOpened to False
        """
        del self.CR2_SLICES
        del self.IFD3
        del self.IFD0
        del self.Sensor
        del self.MAKERNOTES
        del self.EXIF
        self.fp.close()
        self.isOpened = False

    def extractEmbeddedJpeg(self):
        """
        Read the interpolated RGB jpeg image from the CR2 file.

        --- NOT IMPLEMENTED YET ---
        """
        raise NotImplementedError("Function not implemented yet")

    def decodeRawImage(self):
        """
        Decode the RAW lossless jpeg data using the
        native pure-python decoder

        Returns
        -------
        image : numpy.ndarray or None
            the decompressed full-sensor image
            or None if the decoding process failed
        """

        log.log(tr(msg.DBG_DECODER_NATIVE),
                logging.DEBUG)

        self.fp.seek(self.CR2_SLICES[0], 0)
        rawdata = self.fp.read(self.CR2_SLICES[2])

        if rawdata[-2:] != EOI_MARKER:
            raise SyntaxError(tr(msg.ERR_MARKER_EOI))
        else:
            image_data_end = len(rawdata) - 2

        if rawdata[0:2] != SOI_MARKER:
            raise SyntaxError(tr(msg.ERR_MARKER_SOI))
        else:
            image_data_start = None

        hts = {}
        # parsing jpeg codes
        i = rawdata.find(b'\xff', 0)

        while (i >= 0):
            # JEPG uses Big Endian, regardless of the file byte ordering
            sect_len = _reconstructDataFromString('MM', rawdata[i+2:i+4]) + 2
            if rawdata[i+1] == b'\x00':
                pass
            elif rawdata[i:i+2] == SOI_MARKER:
                pass
            elif rawdata[i:i+2] == DHT_MARKER:
                h = HuffmanTable(rawdata[i:i+sect_len])
                hts[DHT_MARKER] = h
            elif rawdata[i:i+2] == SOF_MARKER:
                hts[SOF_MARKER] = FrameTable(rawdata[i:i+sect_len])
            elif rawdata[i:i+2] == SOS_MARKER:
                hts[SOS_MARKER] = ScanTable(rawdata[i:i+sect_len])
                image_data_start = i + sect_len
            elif rawdata[i:i+2] == EOI_MARKER:
                pass
            i = rawdata.find(b'\xff', i+1)

        if type(rawdata) == bytes:
            imdata = rawdata[image_data_start:image_data_end]
            imdata = imdata.replace(b'\xff\x00', b'\xff')
        else:
            imdata = rawdata[image_data_start:image_data_end]
            imdata = imdata.replace('\xff\x00', '\xff')
            imdata = bytearray(imdata)

        del rawdata

        img = self.decompressLosslessJpeg(imdata, hts)

        del imdata

        return img

    def decodeExternalDecoder(self):
        """
        Decode the RAW lossless jpeg data using the
        external decoder program

        Returns
        -------
        image : numpy.ndarray or None
            the decompressed full-sensor image
            or None if the decoding process failed

        See also
        --------
        pgm2numpy
        """
        if not self.hasExternalDecoder():
            return None

        log.log(tr(msg.DBG_DECODER_EXT),
                logging.DEBUG)

        dec_cmd = self.decoder_fmt.format(
            exec=self.decoder_exec,
            file=self.filename
        )

        p = subprocess.Popen(dec_cmd.split(),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        if p.returncode is not None:
            log.log(
                tr(msg.ERR_EXT_DECODER).format(
                    str(self.decoder_exec),
                    str(p.stderr.read())
                ),
                logging.ERROR)

        pgm_data = p.stdout.read()

        return pgm2numpy(pgm_data)

    def decompressLosslessJpeg(self, data, hts):
        """
        Native pure-python lossless jpeg decoder

        As written in CR2 specifications(1), the image is divided into
        several vertical slices (from lef to right) and then each slice
        is compressed by an huffman encoder.

        Here is an example of an image divided into 3 slices:

                      [a] RAW IMAGE FROM SENSOR
        +--------------------------------------------------+
        |<...............<:::::::::::::::<=================|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |....SLICE  1....::::SLICE  2::::=====SLICE  3=====|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |................::::::::::::::::==================|
        |...............>:::::::::::::::>=================>|
        +--------------------------------------------------+

                                  |
                                  V

                       [b] COMPRESSION PROCESS
                   +-----------------+
                   | HUFFMAN ENCODER |
        <011011010 |                 |..> <SLICE2> <SLICE3>
                   |  out <----- in  |
                   +-----------------+

                                  |
                                  V

        The huffman encoder, however, expects the image is passed as
        a sequence of rows, for this reason it "sees" the vertical
        slices as horizontal bunches of pixels.

            [c] RAW IMAGE AS SEEN BY THE HUFFMAN ENCODER
        +--------------------------------------------------+
        |<.................................................|
        |..................................SLICE  1........|
        |..................................................|
        |.........................................><:::::::|
        |::::::::::::::::::::::::::::::::::::::::::::::::::|
        |::::::::::::::::::::::::::SLICE  2::::::::::::::::|
        |::::::::::::::::::::::::::::::::::::::::::::::::::|
        |:::::::::::::::::::::::::::::::::><===============|
        |==================================================|
        |=============================SLICE  3=============|
        |==================================================|
        |=================================================>|
        +--------------------------------------------------+

                                  |
                                  V

        For this reason we cannot decode each slice directly or we will
        have some strange results (I've tried it XD). To revert back to
        the original RAW image, as written in (2), the compressed image
        must be decoded ROW BY ROW (we know the image shape from the
        FrameTable)

                      [d] DECOMPRESSION PROCESS
                   +-----------------+
                   | HUFFMAN ENCODER |
        <011011010 |                 | row n>...<row 3> <row 2> <row 1>
                   |  in -----> out  |
                   +-----------------+

                                  |
                                  V

        The decoded image is now a perfect copy of the [c] RAW image as
        seen by the huffman encoder of the camera. To obtain the actual
        RAW image the data must be reshaped into vertical slices.

        Parameters
        ----------
            data : byte
                the raw data from CR2 file

            hst : HuffmanTable
                HuffmanTable object for the CR2 file

        Notes
        -----
        For more information see

         (2)  Lossless Jpeg and Huffman decoding:
              http://www.impulseadventure.com/photo/jpeg-huffman-coding.html

         (3) Lossless Jpeg information
             http://www.digitalpreservation.gov/formats/fdd/fdd000334.shtml
        """

        # NOTE: as written in (1) the raw data is encoded as an image
        #       whith 2 (or 4) components, and have the same height of
        #       raw image but only 1/#components of its width
        components = hts[SOF_MARKER].components
        imagew = hts[SOF_MARKER].width * components
        imageh = hts[SOF_MARKER].height

        if (imagew != self.Sensor.width) or (imageh != self.Sensor.height):
            log.log(tr(msg.WRN_CORRUPTED_CR2),
                    logging.WARNING)

        # some usefull constants and variables
        dataend = len(data)
        buff = ba2bs(data[0:TOKENLEN])
        lenbuff = len(buff)
        datapos = TOKENLEN
        dataleft = dataend-TOKENLEN
        half_max_val = (1 << (hts[SOF_MARKER].bits - 1))
        predictor = [half_max_val] * components
        psv = hts[SOS_MARKER].psv

        # computing the size of slices
        if self.CR2_SLICES[1] == 0:
            slices_size = self.imagew
        else:
            slices_size = []
            for i in range(self.CR2_SLICES[1]):
                slices_size.append(self.CR2_SLICES[3])
            slices_size.append(self.CR2_SLICES[4])

        # NOTE: For some unknown reason the code runs much more faster
        #       using python2 instead of python3, probably because
        #       python3 does more checks during execution.

        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
        # NOTE: most of the folloding section is needed to speedup
        #       the decompression process because accessing a local
        #       list or dictionary is faster then accessing class
        #       elements or using the len() function.

        masks = hts[DHT_MARKER].masks[:]
        codes = hts[DHT_MARKER].codes[0, 0]
        same_tables = True

        for c in hts[DHT_MARKER].codes.values():
            same_tables &= (c == codes)

        # If the tables are equal, then switching between them
        # is only a waste of time and only one table will be used
        if same_tables:
            kdic = sorted(codes.keys())
            keys_len = {}
            for k in kdic:
                keys_len[k] = len(k)
        else:
            i = 0
            keys_lens = {}
            kdics = {}
            codes = hts[DHT_MARKER].codes
            indexes = list(codes.keys())
            num_of_indexes = len(indexes)

            # Sorting keys for a faster research
            for c in indexes:
                kdics[c] = sorted(codes[c].keys())
                keys_lens[c] = {}
                for k in kdics[c]:
                    keys_lens[c][k] = len(k)

            kdic = kdics[indexes[0]]
            keys_len = keys_lens[indexes[0]]
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #

        image = []
        rows = range(imageh)
        cols = range(imagew)

        # Decoding data row by row

        if same_tables:

            # NOTE: This IF statement shuold be inside the
            # 'for key in kdic' statement but even a simple
            # IF repeated rows*cols*X times can slow down the
            # code execution. So it is faster to repeat the
            # whole FOR ... FOR block, even if it is not so cool...

            for row in rows:

                # using list and converting to ndarray later
                # is much faster then using ndarray directly!
                crow = []

                for col in cols:

                    if (lenbuff < MIN_BUFFER_LEN):
                        if datapos <= dataleft:
                            buff += ba2bs(data[datapos:datapos+TOKENLEN])
                            lenbuff += bittokenlen
                            datapos += TOKENLEN
                        elif datapos < dataend:
                            buff += ba2bs2(data[datapos:])
                            lenbuff = len(buff)
                            datapos = dataend

                    for key in kdic:
                        off = keys_len[key]
                        if key == buff[0:off]:

                            dlen = codes[key]
                            shift = off+dlen

                            if dlen:
                                sbin = buff[off:shift]
                                # DC additional bits to integer value
                                if sbin[0] == '0':
                                    val = -(int(sbin, 2) ^ masks[dlen])
                                else:
                                    val = int(sbin, 2)
                            else:
                                val = 0

                            if col < components:
                                pred = predictor[col]
                                predictor[col] += val
                            else:

                                try:
                                    pxl = crow[-components]
                                except IndexError:
                                    pxl = 0

                                try:
                                    pxt = image[-1][col]
                                except IndexError:
                                    pxt = 0

                                try:
                                    pxtl = image[-1][col-components]
                                except IndexError:
                                    pxtl = 0

                                pred = getPredictorValue(psv, pxl, pxt, pxtl)

                            crow.append(val+pred)
                            buff = buff[shift:]
                            lenbuff -= shift
                            break

                # This type of check is faster then checking for
                # the correct reading of each huffman key, even
                # if it uses the len() function
                if len(crow) != imagew:
                    raise IOError("Corrupted or invalid CR2 data!")

                image.append(crow)
        else:
            for row in rows:

                # using list and converting to ndarray later
                # is much faster then using ndarray directly!
                crow = []

                for col in cols:

                    if (lenbuff < MIN_BUFFER_LEN):
                        if datapos <= dataleft:
                            buff += ba2bs(data[datapos:datapos+TOKENLEN])
                            lenbuff += bittokenlen
                            datapos += TOKENLEN
                        elif datapos < dataend:
                            buff += ba2bs2(data[datapos:])
                            lenbuff = len(buff)
                            datapos = dataend

                    for key in kdic:
                        off = keys_len[key]
                        if key == buff[0:off]:

                            i += 1
                            idx = indexes[i % num_of_indexes]
                            dlen = codes[idx][key]
                            kdic = kdics[idx]
                            keys_len = keys_lens[idx]
                            shift = off + dlen

                            if dlen:
                                sbin = buff[off:shift]

                                # DC additional bits to integer value
                                if sbin[0] == '0':
                                    val = -(int(sbin, 2) ^ masks[dlen])
                                else:
                                    val = int(sbin, 2)
                            else:
                                val = 0

                            if col < components:
                                pred = predictor[col]
                                predictor[col] += val
                            else:

                                try:
                                    pxl = crow[-components]
                                except IndexError:
                                    pxl = 0

                                try:
                                    pxt = image[-1][col]
                                except IndexError:
                                    pxt = 0

                                try:
                                    pxtl = image[-1][col-components]
                                except IndexError:
                                    pxtl = 0

                                pred = getPredictorValue(psv, pxl, pxt, pxtl)

                            crow.append(val + pred)
                            buff = buff[shift:]
                            lenbuff -= shift
                            break

                # This type of check is faster then checking for
                # the correct reading of each huffman key, even
                # if it uses the len() function
                if len(crow) != imagew:
                    raise IOError("Corrupted or invalid CR2 data!")

                image.append(crow)

        # Now we reorder the decoded image into the original slices
        flattened = np.array(image, dtype=np.uint).flatten('C')
        image = np.empty((imageh, imagew), dtype=np.uint16)
        start = 0
        end = 0

        for s in slices_size:
            end += s
            flatarr = np.array(flattened[imageh*start:imageh*end])
            image[:, start:end] = flatarr.reshape((imageh, s))
            start += s
            del flatarr

        del flattened
        return image

    def _readIfd(self, byteorder, offset):
        """
        Helper function for the native decoder
        """
        self.fp.seek(offset, 0)
        raw_ifd = self.fp.read(2)

        # create IFD tags dictionary
        tags = {}

        for i in range(_reconstructDataFromString(byteorder, raw_ifd)):
            data = self.fp.read(12)
            tagID = _reconstructDataFromString(byteorder, data[:2])
            tagType = _reconstructDataFromString(byteorder, data[2:4])
            tagNum = _reconstructDataFromString(byteorder, data[4:8])
            tagValOff = _reconstructDataFromString(byteorder, data[8:12])

            if (tagNum > 1) or (_getTypeSize(tagType) > 4):
                fppos = self.fp.tell()
                self.fp.seek(tagValOff, 0)
                datasize = _getTypeSize(tagType)
                if datasize == -1:
                    val = _getExifValue(self.fp.read(tagNum), tagType)
                elif datasize == -2:
                    tagVal = _getExifValue(tagValOff, tagType)
                    val = ('undefined', tagNum, tagVal)
                else:
                    val = []
                    for i in range(tagNum):
                        data = self.fp.read(datasize)
                        data_off = _reconstructDataFromString(byteorder, data)
                        tagVal = _getExifValue(data_off, tagType)
                        val.append(tagVal)
                self.fp.seek(fppos, 0)
            else:
                val = _getExifValue(tagValOff, tagType)
            if (type(val) == tuple) or (type(val) == list):
                if len(val) == 1:
                    val = val[0]
            tags[tagID] = val
        return tags


def writeFITS(name, data, compressed=False, header=()):
    """
    Writes a numpy array to a FITS file

    Parameters
    ----------
    name : str
        The name of the FITS file to be saved

    data : numpy.ndarray
        The data to be saved

    compressed : bool
        If true save the data to a compressed
        FITS file.

    header : dict
        a dictionary containing the header CARS
        to be addded to the file. Must have the
        format of

        header = {
            'key1' : ('value1', 'comment1')
            'key2' : ('value2', 'comment2')
            ...
        }

    Returns
    -------
    None
    """

    if compressed:
        # NOTE: cannot compress primary HDU
        hdu = pyfits.PrimaryHDU(header=getFitsStdHeader())
        com = pyfits.CompImageHDU(data, header=getFitsStdHeader())
        for k, v, d in header:
            hdu.header[str(k).upper()] = (v, str(d))
            com.header[str(k).upper()] = (v, str(d))
        hdl = pyfits.HDUList([hdu, com])
    else:
        hdu = pyfits.PrimaryHDU(data, header=getFitsStdHeader())
        for k, v, d in header:
            hdu.header[str(k).upper()] = (v, str(d))
        hdl = pyfits.HDUList([hdu])

    if os.path.exists(name):
        os.remove(name)
    hdl.writeto(name)
