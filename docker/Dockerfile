ARG ubuntu_version=20.04
FROM ubuntu:$ubuntu_version
# needed to do again after FROM due to docker limitation
ARG ubuntu_version

ENV INCONTEXT_DIR /usr/local/src/incontext
WORKDIR ${INCONTEXT_DIR}
COPY docker ${INCONTEXT_DIR}/
RUN bash setup.sh
