from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
from socketserver import TCPServer
import json
import cgi
import os
from pathlib import Path


cpath = Path(os.path.dirname(__file__))

class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
    def do_HEAD(self):
        self._set_headers()
        
    # GET sends back a Hello world message
    def do_GET(self):
        self._set_headers()
        
        pathToFile = {}
        for file in os.listdir(cpath):
            fileAbsPath = cpath/file
            if not fileAbsPath.is_dir() and file.endswith(".json"):
                pathToFile["/{}/{}".format(cpath.name, file)] = fileAbsPath
            
        if self.path in pathToFile:
            self.wfile.write(pathToFile[self.path].read_bytes())
        else:
            self.wfile.write(bytes("Requested path file does not exists!", 'utf-8'))
            self.send_response(400)
            self.end_headers()
            
        
    # def do_POST(self):
    #     # No post
    #     self.send_response(400)
    #     self.end_headers()
    #     return;
       
    #     # POST echoes the message adding a JSON field 
    #     ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        
    #     # refuse to receive non-json content
    #     if ctype != 'application/json':
    #         self.send_response(400)
    #         self.end_headers()
    #         return
            
    #     # read the message and convert it into a python dictionary
    #     length = int(self.headers.getheader('content-length'))
    #     message = json.loads(self.rfile.read(length))
        
    #     # add a property to the object, just to mess with data
    #     message['received'] = 'ok'
        
    #     # send the message back
    #     self._set_headers()
    #     self.wfile.write(json.dumps(message))
        
def run(server_class=TCPServer, handler_class=SimpleHTTPRequestHandler, port=8008):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    
    print('Starting http on port %d...' % port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    
if __name__ == "__main__":
    from sys import argv
    
    if len(argv) == 2:
        run(server_class = TCPServer, handler_class = Server, port=int(argv[1]))
    else:
        run(server_class = TCPServer, handler_class = Server)
        