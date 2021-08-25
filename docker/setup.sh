#!/bin/bash

set -e

export DEBIAN_FRONTEND=noninteractive

# Install the package dependencies.
cd $INCONTEXT_DIR
apt-get update
cat requirements.txt | xargs apt-get install -y

# Timezone support
ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
dpkg-reconfigure --frontend noninteractive tzdata

# Install ImageMagick with HEIC support
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
make
make install
cd /usr/src/libheif/
./autogen.sh
./configure
make
make install
cd /usr/src/
git clone --depth 1 https://github.com/ImageMagick/ImageMagick.git --branch 7.0.11-5 ImageMagick
cd ImageMagick
./configure --with-heic=yes
make
make install
ldconfig

# Install the Python dependencies.
cd $INCONTEXT_DIR
python3 -m pip install pipenv
pipenv install --verbose --system --skip-lock

# Clean up the working directory.
cd /
rm -r $INCONTEXT_DIR
