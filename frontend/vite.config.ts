import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import * as net from 'net'
import * as fs from 'fs'
import * as path from 'path'

function findAvailablePort(startPort: number): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(startPort, () => {
      const port = (server.address() as net.AddressInfo).port
      server.close(() => resolve(port))
    })
    server.on('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE') {
        findAvailablePort(startPort + 1).then(resolve, reject)
      } else {
        reject(err)
      }
    })
  })
}

function getBackendPort(): number {
  try {
    // 读取后端端口配置文件
    const configPath = path.resolve(__dirname, '..', '.port_config.json')
    if (fs.existsSync(configPath)) {
      const data = JSON.parse(fs.readFileSync(configPath, 'utf-8'))
      return data.backend_port || 8000
    }
  } catch (e) {
    console.log('⚠ 无法读取后端端口配置，使用默认端口 8000')
  }
  return 8000
}

export default defineConfig(async () => {
  const port = await findAvailablePort(3000)
  if (port !== 3000) {
    console.log(`\x1b[33m⚠ 端口 3000 已被占用，自动切换到可用端口 ${port}\x1b[0m`)
  }

  // 获取后端实际端口
  const backendPort = getBackendPort()
  if (backendPort !== 8000) {
    console.log(`\x1b[33m⚠ 后端端口已切换到 ${backendPort}，代理目标已更新\x1b[0m`)
  }

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      port: port,
      strictPort: false,
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
          ws: true,
        },
        '/ws': {
          target: `ws://localhost:${backendPort}`,
          ws: true,
        },
      },
    },
  }
})
