#!/usr/bin/sh

echo "Generating man files..."
python generate-man.py

echo "Building source package..."
python setup.py sdist

echo "Done!"
