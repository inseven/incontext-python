#!/bin/bash

set -e
set -x

echo "HELLO!"

# Install the package dependencies.
cd $INCONTEXT_DIR
cat requirements.txt | xargs apk add --no-cache 

# Timezone support
#ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
#dpkg-reconfigure --frontend noninteractive tzdata

#mkdir -p /build-deps

# # libde265
# RUN set -ex \
#     && cd /build-deps \
#     && LIBDE265_VERSION="1.0.5" \
#     && wget https://github.com/strukturag/libde265/releases/download/v${LIBDE265_VERSION}/libde265-${LIBDE265_VERSION}.tar.gz \
#     && tar xvf libde265-${LIBDE265_VERSION}.tar.gz \
#     && cd libde265-${LIBDE265_VERSION} \
#     && ./autogen.sh \
#     && ./configure --prefix /usr \
#     && make -j4 \
#     && make install \
#     && ldconfig

# # libheif
# RUN set -ex \
#     && cd /build-deps \
#     && LIBHEIF_VERSION="1.7.0" \
#     && wget https://github.com/strukturag/libheif/releases/download/v${LIBHEIF_VERSION}/libheif-${LIBHEIF_VERSION}.tar.gz \
#     && tar xvf libheif-${LIBHEIF_VERSION}.tar.gz \
#     && cd libheif-${LIBHEIF_VERSION} \
#     && ./configure --prefix /usr \
#     && make -j4 \
#     && make install \
#     && ldconfig

# # libffi
# RUN set -ex \
#     && cd /build-deps \
#     && LIBFFI_VERSION="3.3" \
#     && wget ftp://sourceware.org/pub/libffi/libffi-${LIBFFI_VERSION}.tar.gz \
#     && tar xvf libffi-${LIBFFI_VERSION}.tar.gz \
#     && cd libffi-${LIBFFI_VERSION} \
#     && ./configure --prefix /usr \
#     && make -j4 \
#     && make install \
#     && ldconfig

# Install ImageMagick with HEIC support
# sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list
# apt-get update
# apt-get install -y build-essential autoconf git-core wget
# apt-get build-dep -y imagemagick libde265 libheif
# cd /usr/src/
# git clone https://github.com/strukturag/libde265.git
# git clone https://github.com/strukturag/libheif.git
# cd libde265/
# ./autogen.sh
# ./configure
# make
# make install
# cd /usr/src/libheif/
# ./autogen.sh
# ./configure
# make
# make install
mkdir -p /usr/src/
cd /usr/src/
wget https://www.imagemagick.org/download/ImageMagick.tar.gz
tar xf ImageMagick.tar.gz
rm ImageMagick.tar.gz
cd ImageMagick-7*
./configure --with-heic=yes --with-tiff=yes
make
make install
# ldconfig

# Install the Python dependencies.
cd $INCONTEXT_DIR
python3 -m pip install pipenv
pip3 install git+https://github.com/david-poirier-csn/pyheif.git
pipenv install --verbose --system --skip-lock

# Install the Ruby dependencies.
gem install sass

# Clean up the working directory.
cd /
rm -r $INCONTEXT_DIR
