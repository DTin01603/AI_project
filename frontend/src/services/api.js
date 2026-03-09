const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim()
const CHAT_ENDPOINT = '/api/v2/chat'

const FALLBACK_MODELS = [
    'gemini/gemini-2.5-flash-lite',
    'gemini/gemini-2.5-flash',
    'groq/llama-3.3-70b-versatile',
    'groq/llama-3.1-8b-instant',
]

function buildEndpoint(path) {
    // Build absolute endpoint when VITE_API_BASE_URL is provided, otherwise use relative path.
    if (!API_BASE_URL) {
        return path
    }
    return `${API_BASE_URL.replace(/\/$/, '')}${path}`
}

function normalizeModels(payload) {
    // Normalize backend model payload into a unique list of available model names.
    const source = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.models)
            ? payload.models
            : []

    const normalized = source
        .map((item) => {
            if (typeof item === 'string') {
                const name = item.trim()
                return name ? { name, available: true } : null
            }

            if (item && typeof item === 'object') {
                const candidate = item.id ?? item.model ?? item.name
                const name = typeof candidate === 'string' ? candidate.trim() : ''
                if (!name) {
                    return null
                }

                return {
                    name,
                    available: typeof item.available === 'boolean' ? item.available : true,
                }
            }

            return null
        })
        .filter(Boolean)

    const allModels = normalized.filter((item) => item.available).map((item) => item.name)

    return [...new Set(allModels)]
}

export async function fetchModels() {
    // Fetch model list with graceful fallback to static defaults.
    try {
        const response = await fetch(buildEndpoint('/models'))
        if (!response.ok) {
            throw new Error('Cannot load models')
        }

        const data = await response.json()
        const models = normalizeModels(data)
        if (models.length > 0) {
            return {
                models: [...new Set([...models, ...FALLBACK_MODELS])],
                usedFallback: false,
                reason: null,
            }
        }

        return {
            models: FALLBACK_MODELS,
            usedFallback: true,
            reason: 'Danh sách model từ backend rỗng, đang dùng danh sách mặc định.',
        }
    } catch {
        return {
            models: FALLBACK_MODELS,
            usedFallback: true,
            reason: 'Không tải được /models từ backend, đang dùng danh sách mặc định.',
        }
    }
}

function parseSSEEventBlock(block) {
    const lines = block.split('\n')
    const dataLines = lines
        .map((line) => line.trim())
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trim())

    if (dataLines.length === 0) {
        return null
    }

    return dataLines.join('\n')
}

export async function sendMessageStream(message, model, conversationId = null, { onEvent } = {}) {
    const payload = {
        message,
        locale: 'vi-VN',
        channel: 'web',
        model,
    }

    if (typeof conversationId === 'string' && conversationId.trim()) {
        payload.conversation_id = conversationId.trim()
    }

    const response = await fetch(buildEndpoint(`${CHAT_ENDPOINT}?stream=true`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-request-id': crypto.randomUUID(),
        },
        body: JSON.stringify(payload),
    })

    if (!response.ok || !response.body) {
        let errorMessage = 'Streaming request failed'
        try {
            const errorBody = await response.json()
            if (typeof errorBody?.detail === 'string' && errorBody.detail.trim()) {
                errorMessage = errorBody.detail
            }
        } catch {
            // no-op
        }
        throw new Error(errorMessage)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
        const { value, done } = await reader.read()
        if (done) {
            break
        }

        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() ?? ''

        for (const block of blocks) {
            const data = parseSSEEventBlock(block)
            if (!data) {
                continue
            }

            if (data === '[DONE]') {
                onEvent?.({ type: 'done_marker' })
                continue
            }

            try {
                const parsed = JSON.parse(data)
                onEvent?.(parsed)
            } catch {
                // ignore malformed SSE chunks
            }
        }
    }

    if (buffer.trim()) {
        const data = parseSSEEventBlock(buffer.trim())
        if (data && data !== '[DONE]') {
            try {
                const parsed = JSON.parse(data)
                onEvent?.(parsed)
            } catch {
                // ignore malformed trailing SSE chunk
            }
        }
    }
}

