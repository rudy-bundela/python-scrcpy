# Build stage
FROM python:3-alpine AS builder

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

# Download and verify scrcpy server
RUN curl -L -o scrcpy-server https://github.com/Genymobile/scrcpy/releases/download/v${SCRCPY_VER}/scrcpy-server-v${SCRCPY_VER} \
    && echo "$SERVER_HASH  /scrcpy-server" | sha256sum -c -

# Build scrcpy
RUN git clone -b turn-off-listening https://github.com/buy-real-code-online/scrcpy-wip scrcpy \
    && cd scrcpy \
    && meson x --buildtype=release --strip -Db_lto=true -Dprebuilt_server=/scrcpy-server \
    && cd x \
    && ninja \
    && ninja install

# Final stage
FROM python:3-alpine

# Set up web application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# Install only runtime dependencies
RUN apk add --no-cache \
    ffmpeg \
    libusb \
    sdl2 \
    android-tools

# Copy only necessary files from builder
COPY --from=builder /usr/local/bin/scrcpy /usr/local/bin/
COPY --from=builder /usr/local/share/scrcpy /usr/local/share/scrcpy
COPY --from=builder /usr/local/bin/mediamtx /usr/local/bin/
COPY ./templates ./templates
COPY ./static ./static
COPY simplewebui.py .

EXPOSE 5000
CMD ["python", "simplewebui.py"]