"""Registry of available models."""

MODEL_REGISTRY = {
    "example-model": {
        "description": "Placeholder model entry.",
        "version": "1.0.0",
    }
}

class ModelRegistry:
    """Access model registry."""

    @staticmethod
    def get(model_name: str):
        """Return information for a registered model."""
        return MODEL_REGISTRY.get(model_name)
