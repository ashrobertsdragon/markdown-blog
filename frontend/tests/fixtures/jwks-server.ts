import { readFileSync } from 'node:fs'
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname: string = dirname(fileURLToPath(import.meta.url))
const jwks: string = readFileSync(join(__dirname, 'test-public-jwks.json'), 'utf8')

const server = createServer((req: IncomingMessage, res: ServerResponse) => {
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
