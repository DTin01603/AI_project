import { useEffect, useRef } from 'react'

function ResponseDisplay({ content, isComplete }) {
    // Optional helper component to preview streaming content and completion state.
    const endRef = useRef(null)

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }, [content])

    if (!content) {
        return null
    }

    return (
        <section className="meta-box" aria-label="streaming response preview">
            <p>
                <strong>Streaming Response</strong>
            </p>
            <p style={{ whiteSpace: 'pre-wrap' }}>{content}</p>
            <p>
                <strong>state:</strong> {isComplete ? 'complete' : 'streaming'}
            </p>
            <div ref={endRef} />
        </section>
    )
}

export default ResponseDisplay
