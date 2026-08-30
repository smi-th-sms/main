import socket
import json

def debug_auto_setup_error():
    HOST = 'localhost'
    PORT = 9876
    
    code = r"""
import hou

def inspect_auto_setup():
    # Find Node
    obj = hou.node("/obj")
    setup_node = obj.node("shot_loader_setup")
    if not setup_node:
        for c in obj.children():
            if c.name() == "shot_loader_setup":
                setup_node = c
                break
    
    if not setup_node: return "Error: shot_loader_setup not found."

    # Check button
    btn_name = "auto_setup_btn"
    parm = setup_node.parm(btn_name)
    if not parm:
        return f"Error: '{btn_name}' parameter not found."
    
    pt = parm.parmTemplate()
    script = pt.scriptCallback()
    
    return f"--- Auto Setup Script ---\n{script}\n-------------------------"

print(inspect_auto_setup())
"""

    command = {
        "type": "execute_code",
        "params": {
            "code": code
        }
    }

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((HOST, PORT))
            s.sendall(json.dumps(command).encode('utf-8'))
            
            data = s.recv(16384)
            response = json.loads(data.decode('utf-8'))
            
            if response.get('status') == 'success':
                result = response.get('result', {})
                print(result.get('stdout', '').strip())
                if result.get('stderr'):
                    print("Stderr:", result.get('stderr'))
            else:
                print("Error:", response.get('message'))
                
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    debug_auto_setup_error()

