from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from langsmith import Client, evaluate


def ensure_dataset(client: Client, dataset_name: str) -> None:
    """Create dataset if it does not exist yet."""
    try:
        client.read_dataset(dataset_name=dataset_name)
    except Exception:
        client.create_dataset(dataset_name=dataset_name)


def ensure_seed_examples(client: Client, dataset_name: str) -> None:
    """Create one demo example when dataset has no examples yet."""
    dataset = client.read_dataset(dataset_name=dataset_name)
    existing = list(client.list_examples(dataset_id=dataset.id, limit=1))
    if existing:
        return

    client.create_examples(
        dataset_id=dataset.id,
        inputs=[{"messages": ["What is AI?"]}],
        outputs=[{"answer": "AI is artificial intelligence."}],
    )


def exact_match(
    outputs: dict[str, Any], reference_outputs: dict[str, Any]
) -> dict[str, float]:
    """Return a numeric score so LangSmith UI always shows evaluator values."""
    return {"key": "exact_match", "score": float(outputs == reference_outputs)}


def predictor(example_input: dict[str, Any]) -> dict[str, Any]:
    """Simple demo predictor used by LangSmith evaluate()."""
    raw_messages = example_input.get("messages", "")
    if isinstance(raw_messages, list):
        message_text = " ".join(str(item) for item in raw_messages)
    else:
        message_text = str(raw_messages)

    return {
        "answer": f"{message_text} is a good question. I don't know the answer."
    }


def main() -> None:
    # Load environment variables (.env) before creating LangSmith client.
    load_dotenv()

    client = Client()
    dataset_name = "Dataset_Dinhtin"

    ensure_dataset(client, dataset_name)
    ensure_seed_examples(client, dataset_name)

    results = evaluate(
        predictor,
        data=dataset_name,
        evaluators=[exact_match],
        experiment_prefix="Dataset_Dinhtin experiment",
    )

    # Keep a stable terminal summary that works across langsmith versions.
    print(f"Experiment: {results.experiment_name}")


if __name__ == "__main__":
    main()
