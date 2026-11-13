import type { ModelInfo, Prediction, RequestBody } from './spec'

export interface FieldIssue {
  field: string | null
  code: string
}

/** `code` is an i18n key under `errors.` */
export class ApiError extends Error {
  code: 'rate_limited' | 'network' | 'server' | 'validation'
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
