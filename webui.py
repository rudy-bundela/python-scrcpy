from flask import Flask, request, render_template_string, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import shlex
import os
import threading
import queue
import pty
import select
import termios
import struct
import fcntl

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active processes
active_processes = {}

# HTML template with basic styling and JavaScript for async requests
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Command Runner</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .input-group {
            margin-bottom: 20px;
        }
        input[type="text"] {
            width: 70%;
            padding: 8px;
            margin-right: 10px;
        }
        button {
            padding: 8px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
        }
        #output {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            white-space: pre-wrap;
            height: 300px;
            overflow-y: auto;
            font-family: monospace;
        }
        #interactive-input {
            display: none;
            margin-top: 10px;
        }
        .interactive-mode {
            background-color: #fff3cd;
        }
    </style>
</head>
<body>
    <h1>Command Runner</h1>
    <div class="input-group">
        <input type="text" id="command" placeholder="Enter command">
        <button onclick="runCommand()">Run</button>
    </div>
    <div id="output"></div>
    <div id="interactive-input" class="input-group">
        <input type="text" id="interactive-command" placeholder="Enter input">
        <button onclick="sendInput()">Send</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        const outputDiv = document.getElementById('output');
        const interactiveInput = document.getElementById('interactive-input');
        let activeProcessId = null;

        socket.on('connect', () => {
            console.log('Connected to server');
        });

        socket.on('output', (data) => {
            outputDiv.innerHTML += data.output + '\\n';
            outputDiv.scrollTop = outputDiv.scrollHeight;
            
            if (data.interactive) {
                interactiveInput.style.display = 'block';
                outputDiv.classList.add('interactive-mode');
                activeProcessId = data.processId;
            }
        });

        socket.on('process_end', () => {
            interactiveInput.style.display = 'none';
            outputDiv.classList.remove('interactive-mode');
            activeProcessId = null;
        });

        function runCommand() {
            const command = document.getElementById('command').value;
            if (!command) return;

            outputDiv.innerHTML = '';
            socket.emit('run_command', { command: command });
            document.getElementById('command').value = '';
        }

        function sendInput() {
            const input = document.getElementById('interactive-command').value;
            if (!input || !activeProcessId) return;

            socket.emit('send_input', {
                input: input + '\\n',
                processId: activeProcessId
            });
            document.getElementById('interactive-command').value = '';
        }

        // Handle Enter key in interactive input
        document.getElementById('interactive-command').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendInput();
            }
        });

        // Handle Enter key in command input
        document.getElementById('command').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                runCommand();
            }
        });
    </script>
</body>
</html>
'''

def create_terminal():
    """Create a new pseudo-terminal."""
    master_fd, slave_fd = pty.openpty()
    # Set raw mode
    term_settings = termios.tcgetattr(slave_fd)
    term_settings[3] = term_settings[3] & ~termios.ECHO
    termios.tcsetattr(slave_fd, termios.TCSADRAIN, term_settings)
    return master_fd, slave_fd

def read_terminal(fd):
    """Read output from terminal."""
    try:
        return os.read(fd, 1024).decode()
    except (OSError, UnicodeDecodeError):
        return ''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('run_command')
def handle_command(data):
    command = data.get('command', '').strip()
    
    # Basic security: prevent empty or dangerous commands
    if not command:
        emit('output', {'output': 'No command provided', 'error': True})
        return

    # List of allowed commands for security
    allowed_commands = ['ls', 'pwd', 'date', 'whoami', 'uname', 'adb', 'scrcpy', 'ffmpeg', 'cd']
    command_base = shlex.split(command)[0]
    
    if command_base not in allowed_commands:
        emit('output', {
            'output': f'Command not allowed. Allowed commands: {", ".join(allowed_commands)}',
            'error': True
        })
        return

    # Create pseudo-terminal
    master_fd, slave_fd = create_terminal()
    
    # Start the process
    process = subprocess.Popen(
        shlex.split(command),
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        text=True
    )
    
    # Store process information
    process_id = str(process.pid)
    active_processes[process_id] = {
        'process': process,
        'master_fd': master_fd,
        'slave_fd': slave_fd
    }
    
    def monitor_output():
        while True:
            if process.poll() is not None:
                break
                
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                output = read_terminal(master_fd)
                if output:
                    socketio.emit('output', {
                        'output': output,
                        'processId': process_id,
                        'interactive': True
                    })
        
        socketio.emit('process_end')
        os.close(master_fd)
        os.close(slave_fd)
        del active_processes[process_id]
    
    # Start monitoring thread
    threading.Thread(target=monitor_output, daemon=True).start()

@socketio.on('send_input')
def handle_input(data):
    process_id = data.get('processId')
    user_input = data.get('input', '')
    
    if process_id not in active_processes:
        return
        
    process_info = active_processes[process_id]
    os.write(process_info['master_fd'], user_input.encode())

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
