from http.server import BaseHTTPRequestHandler
import base64
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        expected_auth = "Basic " + base64.b64encode(b"woomin:1234").decode('ascii')
        
        if auth_header != expected_auth:
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Parents Dashboard"')
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("<h1>인증이 필요합니다 (Authentication Required)</h1>".encode('utf-8'))
            return

        html_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'parents.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
