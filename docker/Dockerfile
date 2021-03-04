ARG ubuntu_version=20.04
FROM ubuntu:$ubuntu_version
# needed to do again after FROM due to docker limitation
ARG ubuntu_version

ARG DEBIAN_FRONTEND=noninteractive

ENV INCONTEXT_DIR /usr/local/src/incontext

# Install the package dependencies.
WORKDIR ${INCONTEXT_DIR}
COPY . ${INCONTEXT_DIR}/
RUN apt-get update
RUN bash -c "cat docker/requirements.txt | xargs apt-get install -y"

RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
RUN dpkg-reconfigure --frontend noninteractive tzdata

# Install ImageMagick with HEIC support
WORKDIR ${INCONTEXT_DIR}/docker
RUN bash install_imagemagick.sh

# Install the Python dependencies.
WORKDIR ${INCONTEXT_DIR}/docker
RUN python3 -m pip install pipenv
RUN pipenv install --verbose --system --skip-lock
