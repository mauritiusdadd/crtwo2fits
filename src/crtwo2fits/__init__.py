# cr2 is a program to convert CR2 files into FITS images
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
# NOTE: This script is based on the cr2plugin module of lxnstack
#       but has evolved as a standalone script to directly decode CR2
#       files


"""
 crtwo2fits

 crtwo2fits is a native python module which provides the basic classes
 and functions to convert CR2 files into FITS images.

 Use the help command on each submodule to access its documentation.
 The following submodules are available:

    cr2 - provides the CR2Image classes and FITS conversion functions.
    log - provide custom logging funtions.

"""


import os
import re
import sys
import shutil
import gettext
import argparse
import configparser
import logging
import logging.handlers
import pickle
import platform

import astropy.time as atime

from . import log
from . import cr2


__all__ = ['cr2', 'log']


if platform.system() == 'Linux' or platform.system() == 'Darwin':
    DEFAULT_DCRAW_EXC = shutil.which('dcraw')
    DEFAULT_DCRAW_FMT = '{exec} -t 0 -j -4 -W -D -d -c {file}'

    SYSTEM_CONFIG = os.path.join(
        '/', 'etc', 'crtwo2fits.conf'
    )

    USER_CONFIG = os.path.join(
        os.path.expanduser('~'), '.config', 'crtwo2fits.conf'
    )


TEST_FILES_CR2 = [
    "colorchecker"
]


def getTestFiles(filenames):
    return [os.path.join(cr2.DATADIR, f"{x}.CR2") for x in filenames]


def main():

    try:
        tr = gettext.translation('mainapp', cr2.LOCALEDIR)
    except FileNotFoundError:
        tr = gettext.gettext
    else:
        tr = tr.gettext

    # setting logger constants
    cons_format_str = '%(levelname)s: %(message)s'
    file_format_str = '[%(levelname)s] %(asctime)s - %(message)s'
    cons_formatter = logging.Formatter(fmt=cons_format_str)
    file_formatter = logging.Formatter(fmt=file_format_str)

    # create configparser
    config = configparser.ConfigParser()

    # create argument parser
    parser = argparse.ArgumentParser(
        description=tr('Converts CR2 raw files to FITS images')
    )

    parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                        help=tr('paths of the CR2 file to convert'))

    parser.add_argument('-c', '--compressed', action='store_true',
                        help=tr('Save to a compressed FITS file'))

    parser.add_argument('-e', '--export-exif', action='store_true',
                        help=tr('export EXIF data to a file named FILE.exif'))

    parser.add_argument('-f', '--full-frame', action='store_true',
                        help=tr('Return full sensor image'))

    parser.add_argument('-l', '--log-file', metavar='LOGFILE',
                        const='crtwo2fits.log', nargs='?',
                        help=tr('write the log to the file %(metavar)s. If no '
                                'file is specified, then crtwo2fits.log is '
                                'used by default'))

    parser.add_argument('-n', '--native-decoder', action='store_true',
                        help=tr('use the built-in decoder instead of '
                                'the external one'))

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help=tr('increase the output verbosity level'))

    args = parser.parse_args()

    # setting console verbosity
    if args.verbose == 1:
        verbosity = logging.INFO
    elif args.verbose >= 2:
        verbosity = logging.DEBUG
    else:
        verbosity = logging.WARNING

    # creating logger
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(cons_formatter)
    console_handler.setLevel(verbosity)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    if args.log_file is not None:
        file_handler = logging.handlers.RotatingFileHandler(
            args.log_file,
            backupCount=0)
        file_handler.doRollover()
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(min(verbosity, logging.INFO))
        logger.addHandler(file_handler)
        log.log(tr("logging to the file '{}'").format(args.log_file),
                logging.DEBUG)

    # reading systemwide configuration
    if not config.read(SYSTEM_CONFIG):
        log.log(
            tr("Cannot read system configuration file, using default setting"),
            logging.DEBUG
        )

    # reading user configuration
    if config.read(USER_CONFIG):
        log.log(tr("Found user configuration file"),
                logging.DEBUG)

    dec_exc = DEFAULT_DCRAW_EXC
    dec_fmt = DEFAULT_DCRAW_FMT

    # parsing configuration
    try:
        main_section = config['CONFIG']

        try:
            dec_sec_name = main_section['external-decoder'].upper()
        except KeyError:
            pass
        else:
            try:
                decoder_section = config[dec_sec_name]
            except KeyError:
                log.log(
                    tr("Cannot find the section '{}'").format(dec_sec_name),
                    logging.ERROR)
            else:
                try:
                    exec_name = decoder_section['exec']
                    exec_cmd = decoder_section['command'][1:-1]
                except KeyError as exc:
                    log.log(
                        tr("Invalid or corrupted configuration: Key '{}' not "
                           "found in section '{}'\nfalling back to default "
                           "values...").format(exc.args[0], dec_sec_name),
                        logging.ERROR
                    )
                else:
                    dec_exc = shutil.which(exec_name)
                    dec_fmt = re.sub(r'\${([a-zA-Z0-9]*)}', r'{\1}', exec_cmd)
    except KeyError:
        log.log(
            tr("Invalid or corrupted configuration: 'CONFIG' section is "
               "missing!\nfalling back to default values..."),
            logging.ERROR
        )

    # decoding files
    nfiles = len(args.files)
    count = 1
    for fname in args.files:
        log.log(tr("Decoding file {0}/{1}: '{2:s}'").format(
                    count,
                    nfiles,
                    fname),
                logging.INFO)
        count += 1

        cr2img = cr2.CR2Image(fname,
                              ext_decoder=dec_exc,
                              decoder_fmt_str=dec_fmt)

        basename = os.path.splitext(fname)[0]
        fitsname = basename+'.fits'
        exifname = basename+'.exif'

        data = cr2img.load(
            fname,
            ifd=3,
            full_frame=args.full_frame,
            native_decoder=args.native_decoder)

        if data is None:
            sys.exit(1)

        if args.export_exif:
            properties = {}
            for k, v in cr2img.EXIF.items():  # READING EXIF
                if (k == 306) or (k == 36867) or (k == 36868):
                    date = re.findall(r'\d+\.?\d*', v)
                    isostr = '{}-{}-{}T{}:{}:{}'.format(*date)
                    ctime = atime.Time(isostr, format='isot')
                    properties['UTCEPOCH'] = ctime.unix
                if k in cr2.EXIF_TAGS:
                    # self.addProperty(EXIF_TAGS.TAGS[k], v)
                    properties[cr2.EXIF_TAGS[k]] = v
                else:
                    properties[k] = v

            for k, v in cr2img.MAKERNOTES.items():
                properties[('MAKERNOTE', k)] = v

            log.log(tr("Saving exif to '{}'").format(exifname),
                    logging.DEBUG)

            try:
                f = open(exifname, 'wb')
                pickle.dump(properties, f)
            except Exception as exc:
                log.log(tr("Cannot create file '{}': '{}'").format(
                            exifname,
                            str(exc)
                        ),
                        level=logging.ERROR)
        else:
            pass

        exif_header = []

        for k, v in cr2img.EXIF.items():  # READING EXIF
            if (k == 306) or (k == 36867) or (k == 36868):
                date = re.findall(r'\d+\.?\d*', v)
                isostr = '{}-{}-{}T{}:{}:{}'.format(*date)
                ctime = atime.Time(isostr, format='isot')
                exif_header.append(('DATE-OBS', ctime.isot, 'Obsevatiot time'))
            if k in cr2.EXIF_TAGS:
                # self.addProperty(EXIF_TAGS.TAGS[k], v)
                pass

        log.log(tr("Saving data to '{}'").format(fitsname),
                logging.DEBUG)
        cr2.writeFITS(fitsname, data,
                      compressed=args.compressed,
                      header=exif_header)
