import type { ModelInfo, Prediction, RequestBody } from './spec'

export interface FieldIssue {
  field: string | null
  code: string
}

/** `code` is an i18n key under `errors.` */
export class ApiError extends Error {
  code: 'rate_limited' | 'network' | 'server' | 'validation' | 'not_signed_in' | 'invalid_credentials' | 'not_found'
  issues: FieldIssue[]
  constructor(code: ApiError['code'], issues: FieldIssue[] = []) {
    super(code)
    this.code = code
    this.issues = issues
  }
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init)
  } catch {
    throw new ApiError('network')
  }
}

export async function getModel(): Promise<ModelInfo> {
  const response = await request('/api/v1/model')
  if (!response.ok) throw new ApiError('server')
  return (await response.json()) as ModelInfo
}

export async function predict(body: RequestBody): Promise<Prediction> {
  const response = await request('/api/v1/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (response.ok) return (await response.json()) as Prediction
  if (response.status === 429) throw new ApiError('rate_limited')
  if (response.status === 422) {
    const payload = (await response.json().catch(() => ({}))) as { errors?: FieldIssue[] }
    throw new ApiError('validation', payload.errors ?? [])
  }
  throw new ApiError('server')
}

// ---- Accounts and saved history (only used when the server has the feature on) ----

export interface Me {
  email: string
  role: string
  csrf_token: string
}

export interface SavedItem {
  id: string
  created_at: string
  case_code: string | null
  model_version: string
  inputs: Record<string, number | boolean>
  outputs: {
    log_risk: number
    survival: { day_7: number; day_28: number; day_100: number }
    curve?: number[]
    warnings: string[]
  }
}

async function failure(response: Response): Promise<ApiError> {
  if (response.status === 429) return new ApiError('rate_limited')
  const payload = (await response.json().catch(() => ({}))) as { errors?: FieldIssue[] }
  const issues = payload.errors ?? []
  const code = issues[0]?.code
  if (response.status === 401) return new ApiError(code === 'invalid_credentials' ? code : 'not_signed_in')
  if (response.status === 404) return new ApiError('not_found')
  if (response.status === 422) return new ApiError('validation', issues)
  return new ApiError('server')
}

async function send<T>(path: string, method: string, csrf?: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (csrf) headers['X-CSRF-Token'] = csrf
  const response = await request(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  })
  if (!response.ok) throw await failure(response)
  return (response.status === 204 ? undefined : await response.json()) as T
}

export const getFeatures = async (): Promise<{ accounts: boolean }> => {
  const response = await request('/api/v1/features')
  return response.ok ? ((await response.json()) as { accounts: boolean }) : { accounts: false }
}
export const getMe = () => send<Me>('/api/v1/auth/me', 'GET')
export const login = (email: string, password: string) =>
  send<Me>('/api/v1/auth/login', 'POST', undefined, { email, password })
export const logout = (csrf: string) => send<void>('/api/v1/auth/logout', 'POST', csrf)
export const saveCalculation = (csrf: string, inputs: RequestBody, caseCode: string | null) =>
  send<SavedItem>('/api/v1/calculations', 'POST', csrf, caseCode ? { inputs, case_code: caseCode } : { inputs })
export const listCalculations = async () =>
  (await send<{ items: SavedItem[] }>('/api/v1/calculations', 'GET')).items
export const getCalculation = (id: string) =>
  send<SavedItem>(`/api/v1/calculations/${encodeURIComponent(id)}`, 'GET')
export const deleteCalculation = (csrf: string, id: string) =>
  send<void>(`/api/v1/calculations/${encodeURIComponent(id)}`, 'DELETE', csrf)
export const EXPORT_URL = '/api/v1/calculations/export.csv'
