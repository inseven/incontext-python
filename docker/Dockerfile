FROM alpine:3.14

ENV INCONTEXT_DIR /usr/local/src/incontext
WORKDIR ${INCONTEXT_DIR}
COPY docker ${INCONTEXT_DIR}/
RUN apk add --no-cache bash
RUN apk add --no-cache findutils
RUN cat "${INCONTEXT_DIR}/requirements.txt"
RUN bash setup.sh
