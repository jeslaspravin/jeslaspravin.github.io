Serve the jsons from Blog project root use [Python Server](https://docs.python.org/3/library/http.server.html#http.server.SimpleHTTPRequestHandler)

Use one of following commands. However using python's `http.server with -m switch` is not allowing CORS access

> `python ServeJson.py `*`{{port}}`* Or Just `python ServeJson.py `
>
> `python -m http.server 8008 --bind 127.0.0.1`
>
> `python -m http.server --directory `*`{{Directory}}`*
