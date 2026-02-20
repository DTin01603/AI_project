# LangGraph Nodes and Edges

```mermaid
# Cac nut va canh LangGraph

```mermaid
flowchart LR
    UI[React UI] --> API[Python API]
    API --> Entry[LangGraph Entry]

    Entry --> Normalize[normalizeRequest]
    Normalize --> Intent[inferIntentAndConstraints]
    Intent --> Plan[decomposeTasks]

    Plan -->|needs search| SearchRoute{scheduleSearchIfNeeded}
    SearchRoute -->|yes| Enqueue[enqueueSearchJob]
    Enqueue --> Search[executeSearchJob]
    Search --> Docs[retrieveDocuments]
    Docs --> ReturnSearch[returnSearchResults]
    SearchRoute -->|no| Dispatch[dispatchTasks]
    ReturnSearch --> Dispatch

    Dispatch --> External[callExternalAPIs]
    External --> Aggregate[aggregateExecutionResults]

    Aggregate --> Context[resolveContextForModels]
    Context --> Invoke[invokeModelsWithContext]
    Invoke --> Compose[composeResponse]

    Compose --> Log[logMetrics]
    Log --> Deliver[deliverResponseToUser]
    Deliver --> API
    API --> UI
```
