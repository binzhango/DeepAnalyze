"""
DeepAnalyze API Package
OpenAI-compatible API server for DeepAnalyze model
"""

__version__ = "1.0.0"
__title__ = "DeepAnalyze OpenAI-Compatible API"

# Lazy imports to avoid loading heavy dependencies during testing
def __getattr__(name):
    if name == "create_app":
        from .main import create_app
        return create_app
    elif name == "main":
        from .main import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["create_app", "main"]