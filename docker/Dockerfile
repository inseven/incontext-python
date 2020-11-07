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

# Unfortunately the ARM build of Ubuntu 20.04 doesn't seem to have a sufficiently up to date version of libhef, meaning
# that the Python dependencies will fail to build. Instead, we download the source directly and compile it on both
# ARM and Intel for consistency.
WORKDIR /usr/local/src/
RUN git clone https://github.com/strukturag/libheif.git --branch v1.9.1
WORKDIR /usr/local/src/libheif
RUN ./autogen.sh
RUN ./configure
RUN make
RUN make install

# Install the Python dependencies.
WORKDIR ${INCONTEXT_DIR}
COPY Pipfile ${INCONTEXT_DIR}/
RUN python3 -m pip install pipenv
RUN pipenv install --verbose --system --skip-lock
