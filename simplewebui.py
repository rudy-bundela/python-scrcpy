import flask
import subprocess


app = flask.Flask(__name__)

@app.route("/")
def home():
    result = subprocess.run(["ls", "-la"], capture_output=True)
    output = str(result.stdout, 'utf-8')
    return flask.render_template("index.html", output=output)

@app.route("/adb_pair", methods=["POST"])
def adb_pair():
    data = flask.request.get_json()
    pairing_ip = data.get("pairing_ip")
    pairing_port = data.get("pairing_port")
    pairing_code = data.get("pairing_code")
    print(f"Received ADB Pairing IP: {pairing_ip}, Port: {pairing_port}, Code: {pairing_code}")

    proc = subprocess.Popen(["adb", "pair", pairing_ip + ":" + pairing_port], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        output, error = proc.communicate(input=pairing_code, timeout=1)
    except TimeoutError:
        proc.kill()
        print("Process timed out")
        output, error = proc.communicate()

    print("Output:", output)
    print("Error:", error)
    if proc.returncode != 0:
        print("Process failed")
        return {"success": "false"}

    return {"success": "true"}

@app.route("/adb_connect", methods=["POST"])
def adb_connect():
    data = flask.request.get_json()
    connection_ip = data.get("connection_ip")
    connection_port = data.get("connection_port")
    print(f"Received ADB Connection IP: {connection_ip}, Port: {connection_port}")

    proc = subprocess.Popen(["adb", "connect", connection_ip + ":" + connection_port], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        output, error = proc.communicate()
    except TimeoutError:
        proc.kill()
        print("Process timed out")
        output, error = proc.communicate()

    print("Output:", output)
    print("Error:", error)
    if proc.returncode != 0:
        print("Process failed")
        return {"success": "false"}

    return {"success": "true"}

@app.route("/scrcpy_start", methods=["POST"])
def scrcpy_start():

    default_settings = {
        "video_codec": "h264",
        "video_source": "camera",
        "camera_id": "0",
        "bitrate": "5000000",
        "camera_size": "1280x720",
        "camera_fps": "120"
    }

    data = flask.request.get_json()
    video_codec = data.get("scrcpy_start.video_codec", default_settings["video_codec"])
    video_source = data.get("scrcpy_start.video_source", default_settings["video_source"])
    camera_id = data.get("scrcpy_start.camera_id", default_settings["camera_id"])
    bitrate = data.get("scrcpy_start.bitrate", default_settings["bitrate"])
    camera_size = data.get("scrcpy_start.camera_size", default_settings["camera_size"])
    camera_fps = data.get("scrcpy_start.camera_fps", default_settings["camera_fps"])

    command = [
        "scrcpy",
        "-ra.mp4",
        f"--video-codec={video_codec}",
        f"--video-source={video_source}",
        f"-b {bitrate}",
        f"--camera-high-speed",
        f"--camera-id={camera_id}",
        f"--camera-size={camera_size}",
        f"--camera-fps={camera_fps}",
        "--no-playback",
        "--no-window",
        "--no-control",
        "--audio-codec=aac"
    ]

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    return {"success": "true"}

@app.route("/scrcpy_stop", methods=["POST"])
def scrcpy_stop():
    proc = subprocess.Popen(["pkill", "-f", "scrcpy"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, error = proc.communicate()
    print("Output:", output)
    print("Error:", error)
    if proc.returncode != 0:
        print("Process failed")
        return {"success": "false"}
    return {"success": "true"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
