from flask import Flask, request, render_template_string, jsonify
import subprocess
import shlex
import os

app = Flask(__name__)

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

    <script>
        async function runCommand() {
            const command = document.getElementById('command').value;
            const outputDiv = document.getElementById('output');
            
            try {
                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ command: command })
                });
                
                const data = await response.json();
                outputDiv.textContent = data.output || data.error;
            } catch (error) {
                outputDiv.textContent = 'Error: Failed to execute command';
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/run', methods=['POST'])
def run_command():
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        # Basic security: prevent empty or dangerous commands
        if not command:
            return jsonify({'error': 'No command provided'})
        
        # List of allowed commands for security
        allowed_commands = ['ls', 'pwd', 'date', 'whoami', 'uname', 'adb', 'scrcpy']
        command_base = shlex.split(command)[0]
        
        if command_base not in allowed_commands:
            return jsonify({'error': f'Command not allowed. Allowed commands: {", ".join(allowed_commands)}'})
        
        # Run the command with safety measures
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return jsonify({
            'output': result.stdout + result.stderr
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timed out'})
    except Exception as e:
        return jsonify({'error': f'Error executing command: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
