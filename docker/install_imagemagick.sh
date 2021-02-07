#!/bin/bash

sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list
apt-get update
apt-get install -y build-essential autoconf git-core wget
apt-get build-dep -y imagemagick libde265 libheif
cd /usr/src/
git clone https://github.com/strukturag/libde265.git
git clone https://github.com/strukturag/libheif.git
cd libde265/
./autogen.sh
./configure
make –j4
make install
cd /usr/src/libheif/
./autogen.sh
./configure
make –j4
make install
cd /usr/src/
wget https://www.imagemagick.org/download/ImageMagick.tar.gz
tar xf ImageMagick.tar.gz
cd ImageMagick-7*
./configure --with-heic=yes
make –j4
make install
ldconfig
