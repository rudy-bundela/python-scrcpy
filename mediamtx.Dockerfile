FROM alpine

RUN apk add --no-cache ffmpeg curl tar

RUN curl -L -o /mediamtx_v1.14.0_linux_amd64.tar.gz https://github.com/bluenviron/mediamtx/releases/download/v1.14.0/mediamtx_v1.14.0_linux_amd64.tar.gz
RUN tar -xzf /mediamtx_v1.14.0_linux_amd64.tar.gz -C / && rm /mediamtx_v1.14.0_linux_amd64.tar.gz

ENTRYPOINT [ "./mediamtx" ]