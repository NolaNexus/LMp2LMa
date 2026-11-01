"""pytest configuration for notebook validation with nbval"""
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "notebook: mark test as notebook validation")
    config.addinivalue_line("markers", "slow: mark test as slow running")

# nbval settings
pytest_plugins = ["nbval"]
