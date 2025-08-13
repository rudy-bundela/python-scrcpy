FROM python:3-alpine

ARG SCRCPY_VER=3.3.1
ARG SERVER_HASH="a0f70b20aa4998fbf658c94118cd6c8dab6abbb0647a3bdab344d70bc1ebcbb8"

RUN apk add --no-cache \
        curl \
        ffmpeg-dev \
        gcc \
        git \
	    libusb-dev \
        make \
        meson \
        musl-dev \
        android-tools \
        sdl2-dev

# RUN PATH=$PATH:/usr/lib/jvm/java-17-openjdk/bin
RUN curl -L -o scrcpy-server https://github.com/Genymobile/scrcpy/releases/download/v${SCRCPY_VER}/scrcpy-server-v${SCRCPY_VER}
RUN echo "$SERVER_HASH  /scrcpy-server" | sha256sum -c -
RUN git clone -b update-recorder.c https://github.com/buy-real-code-online/scrcpy-wip scrcpy
RUN cd scrcpy && meson x --buildtype=release --strip -Db_lto=true -Dprebuilt_server=/scrcpy-server
RUN cd scrcpy/x && ninja
RUN cd scrcpy/x && ninja install

ENTRYPOINT ["bin/sh"]