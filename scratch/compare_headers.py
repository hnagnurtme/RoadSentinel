import socket
import urllib.parse

def get_headers(url_str):
    url = urllib.parse.urlparse(url_str)
    host = url.hostname
    port = url.port or (443 if url.scheme in ("https", "wss") else 80)
    path = url.path or "/"
    
    # Hand-roll WebSocket upgrade request
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if url.scheme in ("https", "wss"):
        import ssl
        context = ssl.create_default_context()
        s = context.wrap_socket(s, server_hostname=host)
        
    try:
        s.connect((host, port))
        s.sendall(request.encode())
        response = s.recv(4096).decode("utf-8", errors="ignore")
        header_part = response.split("\r\n\r\n")[0]
        return header_part
    except Exception as e:
        return f"Error: {e}"
    finally:
        s.close()

print("--- LOCAL HEADERS ---")
print(get_headers("ws://localhost:8000/api/v1/ws/camera"))
print("\n--- PRODUCTION HEADERS ---")
print(get_headers("wss://road-sentinel.trunganh.tech/api/v1/ws/camera"))
