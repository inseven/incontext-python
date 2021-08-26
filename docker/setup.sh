#!/bin/bash

set -e
set -x
set -o pipefail
set -u

# Install the package dependencies.
cd $INCONTEXT_DIR
cat requirements.txt | xargs apk add --no-cache

# Timezone support
#ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
#dpkg-reconfigure --frontend noninteractive tzdata

mkdir -p /usr/src/

# IMAGEMAGICK_COMMIT=fa87fa7287c8275f52b508770c814815ebe61a02

# libde265
cd /usr/src/
git clone --branch v1.0.8 https://github.com/strukturag/libde265.git
cd libde265
./autogen.sh
./configure
make -j8 install

# libheif
cd /usr/src/
git clone --branch v1.12.0 https://github.com/strukturag/libheif.git
cd libheif
./autogen.sh
./configure
make -j8 install

# ImageMagick
cd /usr/src/
git clone https://github.com/ImageMagick/ImageMagick.git
cd ImageMagick
# git checkout ${IMAGEMAGICK_COMMIT} .
./configure \
    --with-heic \
    --with-tiff \
    --with-heic \
    --with-jpeg \
    --with-lcms2 \
    --with-png \
    --with-gslib \
    --with-openexr \
    --with-zlib \
    --with-gs-font-dir=/usr/share/fonts/Type1 \
    --with-threads \
    --with-webp \
    --without-x
make -j8 install

# Install the Python dependencies.
cd $INCONTEXT_DIR
python3 -m pip install pipenv
pip3 install git+https://github.com/david-poirier-csn/pyheif.git
pipenv install --verbose --system --skip-lock

# Install the Ruby dependencies.
# TODO: Ruby SASS is deprecated and should be removed.
gem install sass

# Clean up the working directory.
cd /
rm -r $INCONTEXT_DIR
