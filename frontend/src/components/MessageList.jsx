function MessageList({ messages }) {
    // Render chat transcript and optional source links for assistant messages.
    return (
        <div className="chat-body" role="log" aria-live="polite">
            {messages.map((entry) => (
                <article key={entry.id} className={`message message-${entry.role}`}>
                    <span className="message-role">{entry.role === 'user' ? 'Bạn' : 'AI'}</span>
                    <p>{entry.content}</p>
                    {entry.role === 'assistant' && Array.isArray(entry.sources) && entry.sources.length > 0 && (
                        <div className="message-sources">
                            <strong>Nguồn tham khảo:</strong>
                            <ul>
                                {entry.sources.map((source) => (
                                    <li key={source}>
                                        <a href={source} target="_blank" rel="noreferrer">
                                            {source}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </article>
            ))}
        </div>
    )
}

export default MessageList
