"""Database initialization and deterministic seed entry point."""

from dispatch.dispatch_engine import DispatchEngine


def seed_database() -> None:
    DispatchEngine().initialize()
