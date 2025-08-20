import flask
import subprocess
import json
import os

USER_PREFS_FILE = "user_prefs.json"

def load_user_prefs():
    defaults = {
        "video_codec": "h264",
        "video_source": "camera",
        "camera_id": "0",
        "bitrate": "5000000",
        "camera_size": "1280x720",
        "camera_fps": "120"
    }
    if os.path.exists(USER_PREFS_FILE):
        with open(USER_PREFS_FILE, "r") as f:
            try:
                prefs = json.load(f)
            except Exception:
                prefs = {}
    else:
        prefs = {}
    # Ensure defaults are present
    for k, v in defaults.items():
        if k not in prefs:
            prefs[k] = v
    # Save back if any defaults were missing
    save_user_prefs(prefs)
    return prefs

def save_user_prefs(prefs):
    with open(USER_PREFS_FILE, "w") as f:
        json.dump(prefs, f)

user_prefs = load_user_prefs()
app = flask.Flask(__name__)

@app.route("/adb_status", methods=["GET"])
def adb_status():
    proc = subprocess.Popen(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, error = proc.communicate()
    print("ADB devices output:", output)
    print("ADB devices error:", error)
    # Parse output for connected devices
    lines = output.strip().splitlines()
    connected = False
    device_list = []
    for line in lines[1:]:  # skip header
        if line.strip() and "device" in line:
            device_id = line.split()[0]
            device_list.append(device_id)
            connected = True
    # Update user_prefs
    user_prefs["adb_connected_devices"] = device_list
    user_prefs["adb_connected"] = connected
    save_user_prefs(user_prefs)
    return {
        "connected": connected,
        "devices": device_list,
        "output": output,
        "error": error
    }

@app.route("/user_status", methods=["GET"])
def user_status():
    return {
        "paired": bool(user_prefs.get("adb_pair_guid")),
        "guid": user_prefs.get("adb_pair_guid"),
        "connected": bool(user_prefs.get("adb_connect_ip")),
        "connect_ip": user_prefs.get("adb_connect_ip"),
        "connect_port": user_prefs.get("adb_connect_port")
    }

@app.route("/")
def home():
    return flask.render_template("index.html", user_prefs=user_prefs)

@app.route("/adb_pair", methods=["POST"])
def adb_pair():
    data = flask.request.get_json()
    pairing_ip = data.get("ip", "")
    pairing_port = data.get("port", "")
    pairing_code = data.get("code", "")

    # Save preferences
    user_prefs["adb_pair_ip"] = pairing_ip
    user_prefs["adb_pair_port"] = pairing_port
    save_user_prefs(user_prefs)

    # Persistent check: has user already paired?
    if user_prefs.get("adb_pair_guid"):
        return {"success": "true", "guid": user_prefs["adb_pair_guid"], "already_paired": True}

    # Check if any of the required variables are empty
    if not pairing_ip or not pairing_port or not pairing_code:
        print("Missing required parameters")
        print(f"Received ADB Pairing IP: {pairing_ip}, Port: {pairing_port}, Code: {pairing_code}")
        return {"success": "false", "error": "Missing required parameters"}

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

    # Parse GUID from output (example: 'Successfully paired to ... [guid=adb-XXXX]')
    import re
    guid_match = re.search(r'\[guid=([a-zA-Z0-9\-]+)\]', output)
    if guid_match:
        guid = guid_match.group(1)
        user_prefs["adb_pair_guid"] = guid
        save_user_prefs(user_prefs)
        return {"success": "true", "guid": guid, "already_paired": False}
    else:
        return {"success": "true", "guid": None, "already_paired": False}

@app.route("/adb_connect", methods=["POST"])
def adb_connect():
    data = flask.request.get_json()
    connection_ip = data.get("ip")
    connection_port = data.get("port")
    print(f"Received ADB Connection IP: {connection_ip}, Port: {connection_port}")

    # Save preferences
    user_prefs["adb_connect_ip"] = connection_ip
    user_prefs["adb_connect_port"] = connection_port
    save_user_prefs(user_prefs)

    # Live check: is device currently connected?
    proc_check = subprocess.Popen(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output_check, error_check = proc_check.communicate()
    lines = output_check.strip().splitlines()
    connected = False
    for line in lines[1:]:  # skip header
        if line.strip() and "device" in line:
            connected = True
            break
    if connected:
        user_prefs["adb_connect_status"] = "connected"
        save_user_prefs(user_prefs)
        return {
            "success": "true",
            "connected": True,
            "connect_ip": user_prefs.get("adb_connect_ip"),
            "connect_port": user_prefs.get("adb_connect_port")
        }

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
        user_prefs["adb_connect_status"] = "failed"
        save_user_prefs(user_prefs)
        return {"success": "false"}

    # Mark as connected
    user_prefs["adb_connect_status"] = "connected"
    save_user_prefs(user_prefs)
    return {
        "success": "true",
        "connected": True,
        "connect_ip": connection_ip,
        "connect_port": connection_port
    }

@app.route("/scrcpy_start", methods=["POST"])
def scrcpy_start():
    data = flask.request.get_json()
    video_codec = data.get("scrcpy_start.video_codec", user_prefs.get("video_codec"))
    video_source = data.get("scrcpy_start.video_source", user_prefs.get("video_source"))
    camera_id = data.get("scrcpy_start.camera_id", user_prefs.get("camera_id"))
    bitrate = data.get("scrcpy_start.bitrate", user_prefs.get("bitrate"))
    camera_size = data.get("scrcpy_start.camera_size", user_prefs.get("camera_size"))
    camera_fps = data.get("scrcpy_start.camera_fps", user_prefs.get("camera_fps"))

    # Save preferences
    user_prefs["video_codec"] = video_codec
    user_prefs["video_source"] = video_source
    user_prefs["camera_id"] = camera_id
    user_prefs["bitrate"] = bitrate
    user_prefs["camera_size"] = camera_size
    user_prefs["camera_fps"] = camera_fps
    save_user_prefs(user_prefs)

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

@app.route("/camera_sizes", methods=["GET"])
def camera_sizes():
    proc = subprocess.Popen(["scrcpy", "--list-camera-sizes"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, error = proc.communicate()
    print("scrcpy camera sizes output:", output)
    print("scrcpy camera sizes error:", error)
    sizes = {}
    current_id = None
    current_info = None
    normal_sizes = []
    high_speed_sizes = []
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith('--camera-id='):
            # Save previous camera block
            if current_id is not None:
                sizes[current_id] = {
                    'info': current_info,
                    'normal': normal_sizes,
                    'high_speed': high_speed_sizes
                }
            # Start new camera block
            current_id = line.split()[0].replace('--camera-id=', '')
            current_info = line[len('--camera-id='):].strip()
            normal_sizes = []
            high_speed_sizes = []
        elif line.startswith('- '):
            # Normal size
            size = line[2:].strip()
            if '(fps=' in size:
                # High speed size
                high_speed_sizes.append(size)
            else:
                normal_sizes.append(size)
        elif line.startswith('High speed capture'):
            # Next lines will be high speed sizes
            continue
    # Save last camera block
    if current_id is not None:
        sizes[current_id] = {
            'info': current_info,
            'normal': normal_sizes,
            'high_speed': high_speed_sizes
        }
    return {
        "success": True,
        "sizes": sizes,
        "output": output,
        "error": error
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
