# Simple Python JSON Server

Serve the jsons from Blog project root use [Python Server](https://docs.python.org/3/library/http.server.html#http.server.SimpleHTTPRequestHandler)

Use one of following commands. However using python's `http.server with -m switch` is not allowing CORS access

> `python ServeJson.py`*`{{port}}`* Or Just `python ServeJson.py`
>
> `python -m http.server 8008 --bind 127.0.0.1`
>
> `python -m http.server --directory`*`{{Directory}}`*

Instead of using this server to serve the json, you could serve the blog webpage itself as it also serves the json. However this script will be useful if ruby and jekyll is not available.
