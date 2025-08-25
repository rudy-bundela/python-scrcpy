from venv import logger
import quart
import subprocess
import json
import os
import asyncio
import time

USER_PREFS_FILE = "user_prefs.json"
MEDIAMTX_STREAM = False  # Set to True if you want to use MediaMTX for streaming

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
app = quart.Quart(__name__)

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
async def home():
    return await quart.render_template("index.html", user_prefs=user_prefs)

@app.route("/adb_pair", methods=["POST"])
async def adb_pair():
    data = await quart.request.get_json()
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
async def adb_connect():
    data = await quart.request.get_json()
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
async def scrcpy_start():
    data = await quart.request.get_json()
    video_codec = data.get("scrcpy_start.video_codec", user_prefs.get("video_codec"))
    video_source = data.get("scrcpy_start.video_source", user_prefs.get("video_source"))
    camera_id = data.get("scrcpy_start.camera_id", user_prefs.get("camera_id"))
    bitrate = data.get("scrcpy_start.bitrate", user_prefs.get("bitrate"))
    camera_size = data.get("scrcpy_start.camera_size", user_prefs.get("camera_size"))
    camera_fps = data.get("scrcpy_start.camera_fps", user_prefs.get("camera_fps"))

    print("camera size: ", camera_size)
    print("camera fps: ", camera_fps)

    # Save preferences
    user_prefs["video_codec"] = video_codec
    user_prefs["video_source"] = video_source
    user_prefs["camera_id"] = camera_id
    user_prefs["bitrate"] = bitrate
    user_prefs["camera_size"] = camera_size
    user_prefs["camera_fps"] = camera_fps
    save_user_prefs(user_prefs)

    # Base command
    command = [
        "scrcpy",
        "-ra.mp4",
        f"--video-codec={video_codec}",
        f"--video-source={video_source}",
        f"-b {bitrate}",
        f"--camera-id={camera_id}",
        "--no-playback",
        "--no-window",
        "--no-control",
        "--audio-codec=aac"
    ]

    # Parse the resolution string
    if "(high speed)" in camera_size:
        # This is a high-speed resolution with embedded fps info
        resolution = camera_size.split()[0]  # Get "1920x1080" from "1920x1080 (fps=[120])"
        command.append("--camera-high-speed")
        command.append(f"--camera-size={resolution}")
        command.append(f"--camera-fps={camera_fps}")  # Default to 120 for high-speed
        # Extract FPS from the string if possible
        # import re
        # fps_match = re.search(r'fps=\[([^\]]+)\]', camera_size)
        # if fps_match:
        #     # Use the first fps value if multiple are present
        #     fps = fps_match.group(1).split(',')[0].strip()
        #     command.append(f"--camera-fps={fps}")
        # else:
        #     command.append(f"--camera-fps={camera_fps}")
    else:
        # Normal resolution
        command.append(f"--camera-size={camera_size}")
        command.append(f"--camera-fps={camera_fps}")

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    import time
    time.sleep(1)  # Give it a moment to start

    if proc.poll() is not None:
        # Process has quit
        output, error = proc.communicate()
        print("Output:", output)
        print("Error:", error)
        return {"success": "false", "error": "scrcpy is still running", "output": output, "error": error}
    return {"success": "true", "output": command}

@app.route("/scrcpy_stop", methods=["POST"])
async def scrcpy_stop():
    proc = subprocess.Popen(["pkill", "-f", "scrcpy"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, error = proc.communicate()
    print("Output:", output)
    print("Error:", error)
    if proc.returncode != 0:
        print("Process failed")
        return {"success": "false", "output": output, "error": error}
    return {"success": "true", "output": output, "error": error}

@app.route("/camera_sizes", methods=["GET"])
async def camera_sizes():
    proc = subprocess.Popen(["scrcpy", "--list-camera-sizes"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, error = proc.communicate()
    print("scrcpy camera sizes output:", output)
    print("scrcpy camera sizes error:", error)
    grouped = {}
    current_id = None
    current_type = None
    fps_list = []
    sizes_by_fps = {}
    high_speed = False
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith('--camera-id='):
            # Save previous camera block
            if current_id is not None:
                if current_type not in grouped:
                    grouped[current_type] = {}
                grouped[current_type][current_id] = sizes_by_fps
            # Start new camera block
            parts = line.split()
            current_id = parts[0].replace('--camera-id=', '')
            # Extract type (front/back) and fps
            type_match = None
            fps_match = None
            import re
            type_match = re.search(r'\((front|back),', line)
            fps_match = re.search(r'fps=\[([^\]]+)\]', line)
            current_type = type_match.group(1) if type_match else 'unknown'
            fps_list = [int(fps.strip()) for fps in fps_match.group(1).split(',')] if fps_match else []
            sizes_by_fps = {fps: [] for fps in fps_list}
            high_speed = False
        elif line.startswith('High speed capture'):
            high_speed = True
        elif line.startswith('- '):
            size = line[2:].strip()
            if high_speed:
                # Parse high speed size and fps
                hs_match = re.match(r'(\d+x\d+) \(fps=\[([^\]]+)\]\)', size)
                if hs_match:
                    res = hs_match.group(1)
                    hs_fps = [int(fps.strip()) for fps in hs_match.group(2).split(',')]
                    for fps in hs_fps:
                        if fps not in sizes_by_fps:
                            sizes_by_fps[fps] = []
                        sizes_by_fps[fps].append(res + " (high speed)")
            else:
                # Normal size, add to all normal fps
                for fps in fps_list:
                    sizes_by_fps[fps].append(size)
    # Save last camera block
    if current_id is not None:
        if current_type not in grouped:
            grouped[current_type] = {}
        grouped[current_type][current_id] = sizes_by_fps
    return {
        "success": True,
        "grouped": grouped,
        "output": output,
        "error": error
    }

@app.route("/server_up")
async def server_up(queue):
    time_now = time.time()
    await queue.put("The time now is " + str(time_now))
    print("Server is up and running")
    return {"success": True, "time": time_now}

@app.route("/server_down")
async def server_down():
    print("Server is down")
    return {"success": True}

# @app.route('/sse')
# async def sse():
#     # Create a queue for communication
#     queue = asyncio.Queue()
    
#     # Start the background task
#     task = asyncio.create_task(time_consuming_task(queue))
    
#     async def event_stream():
#         try:
#             while True:
#                 try:
#                     # Wait for events with timeout to prevent hanging
#                     result = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
#                     if result == "DONE":
#                         yield f"data: {json.dumps({'status': 'complete'})}\n\n"
#                         yield "event: close\ndata: \n\n"
#                         break
#                     else:
#                         yield f"data: {json.dumps({'status': 'progress', 'message': result})}\n\n"
                        
#                 except asyncio.TimeoutError:
#                     # Send heartbeat every 3 seconds to keep connection alive
#                     yield "event: heartbeat\ndata: \n\n"
#                     continue
                    
#         except Exception as e:
#             logger.error(f"SSE error: {e}")
#             yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
#         finally:
#             # Clean up the task
#             task.cancel()
#             try:
#                 await task
#             except asyncio.CancelledError:
#                 pass

#     response = quart.Response(
#         event_stream(),
#         content_type='text/event-stream',
#         headers={
#             'Cache-Control': 'no-cache',
#             'Connection': 'keep-alive',
#             'X-Accel-Buffering': 'no'
#         }
#     )
#     return response

# # Update the time_consuming_task to send proper messages
# async def time_consuming_task(queue):
#     """Simulate a time-consuming task that sends progress updates"""
#     try:
#         for i in range(10):
#             await asyncio.sleep(0.5)  # Simulate work
#             await queue.put(f"Step {i+1}/10 completed")
        
#         await queue.put("DONE")
#     except Exception as e:
#         logger.error(f"Task error: {e}")
#         await queue.put(f"ERROR: {str(e)}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
