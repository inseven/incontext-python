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

LIBDE265_COMMIT=43c490812a6c7b78e9d73125c7e4e2d6ee9826d2
LIBHEIF_COMMIT=0c49d5b4882bcbfc0279dede005832367eb83397
IMAGEMAGICK_COMMIT=fa87fa7287c8275f52b508770c814815ebe61a02

# libde265
cd /usr/src/
git clone -b frame-parallel https://github.com/strukturag/libde265.git
cd libde265
git checkout ${LIBDE265_COMMIT} .
./autogen.sh
./configure
make -j8 install

# libheif
cd /usr/src/
git clone https://github.com/strukturag/libheif.git
cd libheif
git checkout ${LIBHEIF_COMMIT} .
./autogen.sh
./configure
make -j8 install

# ImageMagick
cd /usr/src/
git clone https://github.com/ImageMagick/ImageMagick.git
cd ImageMagick
git checkout ${IMAGEMAGICK_COMMIT} .
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
