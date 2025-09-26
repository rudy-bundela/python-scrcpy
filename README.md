# Phone as a Webcam using Python-Scrcpy

This project converts an Android phone into a webcam, streaming its screen to your web browser using `scrcpy` and Docker.

***

## ⚠️ Project Status

This is a **proof of concept** and is currently a work in progress. It does not have proper error handling and many features are not yet implemented. It is intended for demonstration and development purposes.

***

## Features

* Turns an Android phone into a camera source.
* Streams video to the browser using two different protocols.
    * **WebRTC**: Low-latency stream available at `http://localhost:8888`.
    * **HLS**: HTTP Live Streaming available at `http://localhost:8889`.

***

## Requirements

Before you begin, ensure you have the following:

* An Android phone running **Android 12** or newer.
* **Developer Options and USB Debugging** enabled on the Android device.
* **Docker and Docker Compose** installed on your computer.

***

## Getting Started

Follow these steps to get the video stream running.

### 1. Enable USB Debugging on Your Phone

* On your Android device, go to **Settings** > **About phone**.
* Tap on **Build number** seven times to enable Developer Options.
* Go back to the main Settings menu, find **Developer options**, and turn on **Wireless debugging**.

### 2. Run the Project

1.  Clone the repository to your local machine:
    ```bash
    git clone https://github.com/rudy-bundela/python-scrcpy.git
    cd python-scrcpy
    ```
2.  Start the services using Docker Compose:
    ```bash
    docker compose up
    ```
3. Open `http://localhost:5000` on your browser and follow the instructions on the page to connect your phone

### 3. View the Stream

Once connected you will see a green icon on your phone indicating that the camera is in use and you can access the video stream from your web browser at one of the following addresses:

* **For WebRTC**: `http://localhost:8888`
* **For HLS**: `http://localhost:8889`

***
