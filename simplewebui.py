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

if __name__ == "__main__":
    app.run(debug=True)
