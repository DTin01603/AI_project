import { useState } from 'react'

function MessageInput({ onSend, disabled }) {
    // User input box for composing and submitting chat prompts.
    const [inputValue, setInputValue] = useState('')

    const handleSubmit = (event) => {
        // Validate and forward trimmed message to parent handler.
        event.preventDefault()

        const trimmedMessage = inputValue.trim()
        if (!trimmedMessage || disabled) {
            return
        }

        onSend(trimmedMessage)
        setInputValue('')
    }

    return (
        <form className="chat-form" onSubmit={handleSubmit}>
            <textarea
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                placeholder="Nhập câu hỏi của bạn..."
                rows={3}
                maxLength={4000}
                disabled={disabled}
            />
            <button type="submit" disabled={!inputValue.trim() || disabled}>
                {disabled ? 'Đang gửi...' : 'Gửi'}
            </button>
        </form>
    )
}

export default MessageInput
