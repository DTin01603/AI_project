const MODEL_LABELS = {
    'gemini/gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
    'gemini/gemini-2.5-flash': 'Gemini 2.5 Flash',
    'groq/llama-3.3-70b-versatile': 'Groq Llama 3.3 70B Versatile',
    'groq/llama-3.1-8b-instant': 'Groq Llama 3.1 8B Instant',
    'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
    'gemini-2.5-flash': 'Gemini 2.5 Flash',
    'gemini-3-flash': 'Gemini 3 Flash',
}

function formatModelLabel(model) {
    return MODEL_LABELS[model] ?? model
}

function ModelSelector({ models, selectedModel, onModelChange, disabled }) {
    // Select which backend model to use for the next user request.
    return (
        <div className="model-row">
            <label htmlFor="model">Model</label>
            <select
                id="model"
                value={selectedModel}
                onChange={(event) => onModelChange(event.target.value)}
                disabled={disabled}
            >
                {models.map((model) => (
                    <option key={model} value={model}>
                        {formatModelLabel(model)}
                    </option>
                ))}
            </select>
        </div>
    )
}

export default ModelSelector
