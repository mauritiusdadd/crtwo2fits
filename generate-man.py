#!/usr/bin/env python

import re
import gzip
import time

dic = {
    'date': time.strftime("%Y-%m"),
    'asctime': time.asctime()
}


files = [
    'man/crtwo2fits.1.man',
    'man/crtwo2fits.1.man'
]

if __name__ == '__main__':

    for fname in files:
        inp_f = open(fname, 'r')
        text = inp_f.read()
        inp_f.close
        for key in dic:
            text = re.sub(r'%\('+key+'\)s', dic[key], text)

        out_f = gzip.open(fname[:-4]+'.gz', 'w')
        out_f.write(text.encode('ascii'))
        out_f.close()
