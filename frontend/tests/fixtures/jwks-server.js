const http = require('node:http')
const fs = require('node:fs')
const path = require('node:path')

const jwks = fs.readFileSync(path.join(__dirname, 'test-public-jwks.json'), 'utf8')

const server = http.createServer((req, res) => {
  if (req.url === '/.well-known/jwks.json') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(jwks)
  } else {
    res.writeHead(404)
    res.end()
  }
})

server.listen(5557, '127.0.0.1', () => {
  console.log('JWKS server listening on http://127.0.0.1:5557')
})
