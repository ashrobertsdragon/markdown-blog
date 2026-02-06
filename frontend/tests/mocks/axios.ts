import type { AxiosInstance, AxiosStatic } from 'axios'
import { vi } from 'vitest'

/**
 * Complete axios mock for testing
 *
 * Mocks both the default axios instance (axios.get(), axios.post(), etc.)
 * and the factory method (axios.create())
 */

const mockAxiosGet = vi.fn()
const mockAxiosPost = vi.fn()
const mockAxiosPut = vi.fn()
const mockAxiosDelete = vi.fn()
const mockAxiosPatch = vi.fn()
const mockAxiosRequest = vi.fn()

const mockAxiosInstance: AxiosInstance = {
  get: mockAxiosGet,
  post: mockAxiosPost,
  put: mockAxiosPut,
  delete: mockAxiosDelete,
  patch: mockAxiosPatch,
  request: mockAxiosRequest,
  defaults: {
    headers: {
      common: {},
      delete: {},
      get: {},
      head: {},
      post: {},
      put: {},
      patch: {},
    },
    baseURL: '',
  },
  interceptors: {
    request: { use: vi.fn(), eject: vi.fn(), clear: vi.fn() },
    response: { use: vi.fn(), eject: vi.fn(), clear: vi.fn() },
  },
  getUri: vi.fn(),
  head: vi.fn(),
  options: vi.fn(),
  postForm: vi.fn(),
  putForm: vi.fn(),
  patchForm: vi.fn(),
  formToJSON: vi.fn(),
  create: vi.fn(),
} as unknown as AxiosInstance

const mockAxios: AxiosStatic = {
  ...mockAxiosInstance,
  create: vi.fn(() => mockAxiosInstance),
  isAxiosError: vi.fn(),
  isCancel: vi.fn(),
  all: vi.fn(),
  spread: vi.fn(),
  Cancel: vi.fn(),
  CancelToken: {
    source: vi.fn(),
  },
  Axios: vi.fn(),
  toFormData: vi.fn(),
  formToJSON: vi.fn(),
  AxiosError: vi.fn(),
  HttpStatusCode: {},
  VERSION: '1.0.0',
  getAdapter: vi.fn(),
} as unknown as AxiosStatic

mockAxios.create = vi.fn(() => mockAxiosInstance)

export default mockAxios

export {
  mockAxiosInstance,
  mockAxiosGet,
  mockAxiosPost,
  mockAxiosPut,
  mockAxiosDelete,
  mockAxiosPatch,
  mockAxiosRequest,
}
