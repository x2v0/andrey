import http.server
import socketserver
import os

PORT = 8080
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Логируем только запросы к JS-файлам
        if self.path.endswith('.js'):
            with open("requests.log", "a", encoding="utf-8") as f:
                f.write(self.path + "\n")
        super().do_GET()

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, format, *args):
        if "POST" not in format and "GET /_next" not in format:
            super().log_message(format, *args)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
