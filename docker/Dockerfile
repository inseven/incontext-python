FROM alpine:3.14
# RUN apk add --no-cache mysql-client

ENV INCONTEXT_DIR /usr/local/src/incontext
WORKDIR ${INCONTEXT_DIR}
COPY docker ${INCONTEXT_DIR}/
RUN apk add --no-cache bash
RUN apk add --no-cache findutils
RUN cat "${INCONTEXT_DIR}/requirements.txt"
RUN bash setup.sh



# ARG ubuntu_version=20.04
# FROM ubuntu:$ubuntu_version
# # needed to do again after FROM due to docker limitation
# ARG ubuntu_version

# ENV INCONTEXT_DIR /usr/local/src/incontext
# WORKDIR ${INCONTEXT_DIR}
# COPY docker ${INCONTEXT_DIR}/
# RUN bash setup.sh
