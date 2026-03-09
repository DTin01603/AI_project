import { useEffect, useRef, useState } from 'react'

import MessageInput from './MessageInput'
import MessageList from './MessageList'
import ModelSelector from './ModelSelector'
import { fetchModels, sendMessageStream } from '../services/api'

const CONVERSATION_ID_STORAGE_KEY = 'ai_chat_conversation_id'

function ChatInterface() {
    // Main chat container: orchestrates model selection, message state, and streaming lifecycle.
    const [selectedModel, setSelectedModel] = useState('gemini/gemini-2.5-flash-lite')
    const [availableModels, setAvailableModels] = useState([
        'gemini/gemini-2.5-flash-lite',
        'gemini/gemini-2.5-flash',
        'groq/llama-3.3-70b-versatile',
        'groq/llama-3.1-8b-instant',
    ])
    const [conversationId, setConversationId] = useState(() => {
        if (typeof window === 'undefined') {
            return null
        }

        const saved = window.localStorage.getItem(CONVERSATION_ID_STORAGE_KEY)
        return typeof saved === 'string' && saved.trim() ? saved.trim() : null
    })
    const [isLoadingModels, setIsLoadingModels] = useState(false)
    const [modelsWarning, setModelsWarning] = useState('')
    const [isSending, setIsSending] = useState(false)
    const [error, setError] = useState('')
    const [streamingStatus, setStreamingStatus] = useState(null)
    const [statusEvents, setStatusEvents] = useState([])
    const [lastResponseMeta, setLastResponseMeta] = useState(null)
    const statusEventsRef = useRef(null)
    const [messages, setMessages] = useState([
        {
            id: 'welcome',
            role: 'assistant',
            content: 'Xin chào! Bạn cần mình hỗ trợ gì hôm nay?',
        },
    ])

    useEffect(() => {
        // Load available models on first render.
        const loadModels = async () => {
            setIsLoadingModels(true)
            const result = await fetchModels()
            const models = Array.isArray(result?.models) ? result.models : []

            if (models.length > 0) {
                setAvailableModels(models)
                const preferredModel = models.find((model) => model === 'gemini/gemini-2.5-flash-lite')
                setSelectedModel(preferredModel ?? models[0])
            }

            if (result?.usedFallback) {
                setModelsWarning(
                    typeof result.reason === 'string' && result.reason.trim()
                        ? result.reason
                        : 'Đang dùng danh sách model mặc định do không tải được từ backend.',
                )
            } else {
                setModelsWarning('')
            }

            setIsLoadingModels(false)
        }

        loadModels()
    }, [])

    useEffect(() => {
        if (!statusEventsRef.current) {
            return
        }

        statusEventsRef.current.scrollTop = statusEventsRef.current.scrollHeight
    }, [statusEvents, streamingStatus])

    const handleSendMessage = async (message) => {
        // Submit user message and process SSE events to update UI in realtime.
        if (isSending) {
            return
        }

        setMessages((current) => [
            ...current,
            {
                id: crypto.randomUUID(),
                role: 'user',
                content: message,
            },
        ])

        setError('')
        setStreamingStatus(null)
        setStatusEvents([])
        setIsSending(true)

        try {
            let finalEvent = null

            await sendMessageStream(message, selectedModel, conversationId, {
                onEvent: (event) => {
                    if (!event || typeof event !== 'object') {
                        return
                    }

                    if (event.type === 'status') {
                        const modelRuntime = event.model_runtime || {}
                        setStreamingStatus({
                            message: typeof event.message === 'string' ? event.message : 'Đang xử lý...',
                            node: typeof event.node === 'string' ? event.node : null,
                            progress: typeof event.progress === 'number' ? event.progress : null,
                            model: typeof modelRuntime.model === 'string' ? modelRuntime.model : selectedModel,
                            provider:
                                typeof modelRuntime.provider === 'string' && modelRuntime.provider.trim()
                                    ? modelRuntime.provider
                                    : null,
                        })

                        setStatusEvents((current) => {
                            const nextEvent = {
                                id: crypto.randomUUID(),
                                message: typeof event.message === 'string' ? event.message : 'Đang xử lý...',
                                node: typeof event.node === 'string' ? event.node : 'unknown',
                                progress: typeof event.progress === 'number' ? event.progress : null,
                                timestamp: typeof event.timestamp === 'string' ? event.timestamp : null,
                                model:
                                    typeof modelRuntime.model === 'string' && modelRuntime.model.trim()
                                        ? modelRuntime.model
                                        : selectedModel,
                            }
                            return [...current, nextEvent].slice(-20)
                        })
                        return
                    }

                    if (event.type === 'done') {
                        finalEvent = event
                    }
                },
            })

            if (!finalEvent) {
                throw new Error('Missing done event from streaming response')
            }

            const finalData = finalEvent?.data || {}
            const metadata = finalData.metadata || {}
            const llmMeta = metadata.llm || {}
            const modelRuntime = finalEvent?.model_runtime || {}

            const answer = typeof finalData.answer === 'string' ? finalData.answer : ''
            const sources = Array.isArray(finalData.citations)
                ? finalData.citations.filter((item) => typeof item === 'string' && item.trim())
                : []

            const responseConversationId = metadata.conversation_id
            if (typeof responseConversationId === 'string' && responseConversationId.trim()) {
                const nextConversationId = responseConversationId.trim()
                setConversationId(nextConversationId)
                if (typeof window !== 'undefined') {
                    window.localStorage.setItem(CONVERSATION_ID_STORAGE_KEY, nextConversationId)
                }
            }

            const hasExecutionError = typeof finalData.error === 'string' && finalData.error.trim()
            const responseStatus = hasExecutionError ? 'error' : 'ok'

            setLastResponseMeta({
                request_id: typeof metadata?.request_id === 'string' ? metadata.request_id : null,
                status: responseStatus,
                provider:
                    (typeof modelRuntime.provider === 'string' && modelRuntime.provider.trim()
                        ? modelRuntime.provider
                        : null) ?? llmMeta.provider ?? null,
                model:
                    (typeof modelRuntime.model === 'string' && modelRuntime.model.trim()
                        ? modelRuntime.model
                        : null) ?? llmMeta.model ?? selectedModel,
                finish_reason:
                    (typeof modelRuntime.finish_reason === 'string' && modelRuntime.finish_reason.trim()
                        ? modelRuntime.finish_reason
                        : null) ?? llmMeta.finish_reason ?? null,
                error_code: hasExecutionError ? 'EXECUTION_ERROR' : null,
            })

            setMessages((current) => [
                ...current,
                {
                    id: crypto.randomUUID(),
                    role: 'assistant',
                    content: answer || 'Xin lỗi, hệ thống đang bận. Bạn thử lại giúp mình.',
                    sources,
                },
            ])

            setStreamingStatus((current) => ({
                message: hasExecutionError ? 'Xử lý thất bại' : 'Hoàn tất xử lý',
                node: 'done',
                progress: 100,
                model: current?.model ?? selectedModel,
                provider: current?.provider ?? null,
            }))

            if (hasExecutionError) {
                setError(finalData.error)
            }
        } catch {
            setError('Gửi tin nhắn thất bại. Vui lòng kiểm tra backend và thử lại.')
            setLastResponseMeta({
                request_id: null,
                status: 'error',
                provider: null,
                model: selectedModel,
                finish_reason: null,
                error_code: 'NETWORK_ERROR',
            })
            setStreamingStatus({
                message: 'Không thể nhận luồng phản hồi từ backend',
                node: 'error',
                progress: null,
                model: selectedModel,
                provider: null,
            })
        } finally {
            setIsSending(false)
        }
    }

    return (
        <section className="chat-card">
            <header className="chat-header">
                <h1>AI Chat Assistant</h1>
            </header>

            <ModelSelector
                models={availableModels}
                selectedModel={selectedModel}
                onModelChange={setSelectedModel}
                disabled={isLoadingModels || isSending}
            />
            {modelsWarning && <p className="warning-text">{modelsWarning}</p>}

            <MessageList messages={messages} />

            <section className="status-box" aria-label="streaming status">
                <div className="status-header">
                    <strong>Streaming status</strong>
                    <span>
                        {streamingStatus?.progress != null ? `${streamingStatus.progress}%` : isSending ? '...' : 'Idle'}
                    </span>
                </div>
                <div className="status-events" ref={statusEventsRef}>
                    {streamingStatus && streamingStatus.node !== 'done' ? (
                        <article className="status-event">
                            <div className="status-event-title">
                                <span>{streamingStatus.node ?? 'processing'}</span>
                                <span>{streamingStatus.model ?? selectedModel}</span>
                            </div>
                            <p>{streamingStatus.message}</p>
                            {streamingStatus.provider && <p>provider: {streamingStatus.provider}</p>}
                        </article>
                    ) : null}

                    {statusEvents.map((event) => (
                        <article key={event.id} className="status-event">
                            <div className="status-event-title">
                                <span>{event.node}</span>
                                <span>{event.progress != null ? `${event.progress}%` : '-'}</span>
                            </div>
                            <p>{event.message}</p>
                            <p>model: {event.model}</p>
                        </article>
                    ))}

                    {streamingStatus && streamingStatus.node === 'done' ? (
                        <article className="status-event">
                            <div className="status-event-title">
                                <span>{streamingStatus.node ?? 'processing'}</span>
                                <span>{streamingStatus.model ?? selectedModel}</span>
                            </div>
                            <p>{streamingStatus.message}</p>
                            {streamingStatus.provider && <p>provider: {streamingStatus.provider}</p>}
                        </article>
                    ) : null}

                    {!streamingStatus && !statusEvents.length ? (
                        <p className="status-empty">Chưa có status streaming.</p>
                    ) : null}
                </div>
            </section>

            {error && <p className="error-text">{error}</p>}

            {lastResponseMeta && (
                <section className="meta-box" aria-label="response metadata">
                    <p>
                        <strong>request_id:</strong> {lastResponseMeta.request_id ?? 'N/A'}
                    </p>
                    <p>
                        <strong>status:</strong> {lastResponseMeta.status}
                    </p>
                    <p>
                        <strong>provider:</strong> {lastResponseMeta.provider ?? 'N/A'}
                    </p>
                    <p>
                        <strong>model:</strong> {lastResponseMeta.model ?? 'N/A'}
                    </p>
                    <p>
                        <strong>finish_reason:</strong> {lastResponseMeta.finish_reason ?? 'N/A'}
                    </p>
                    <p>
                        <strong>error_code:</strong> {lastResponseMeta.error_code ?? 'N/A'}
                    </p>
                </section>
            )}

            <MessageInput onSend={handleSendMessage} disabled={isSending} />
        </section>
    )
}

export default ChatInterface
