require("http").createServer((q, r) => r.end("<title>Tiny Node</title>ok")).listen(process.env.PORT || 3000, "127.0.0.1");
