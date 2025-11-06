export interface HeadlessConfig {
  baseUrl: string
}

const defaultPort = Number.parseInt(import.meta.env?.VITE_SOLOGIT_HEADLESS_PORT ?? '1234', 10)
const defaultHost = import.meta.env?.VITE_SOLOGIT_HEADLESS_HOST ?? '127.0.0.1'

export const headlessConfig: HeadlessConfig = {
  baseUrl: `http://${defaultHost}:${defaultPort}`,
}
