#!/usr/bin/bash
./configure
python -m build

cd dist
for package in $(ls crtwo2fits-*.tar.gz); do
    echo "Extracting ${package}..."
    bsdtar -xf $package
    
    pkgdir=${package%.tar.gz}
    echo "Building ${pkgdir}..."
    cd ${pkgdir}
    python setup.py build
    python setup.py install --root="./pkg"
    cd ..
done
