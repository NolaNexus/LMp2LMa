"""pytest configuration for notebook validation.

nbval registers itself as a plugin via its entry point, so no explicit
`pytest_plugins` declaration is needed (and non-root conftest declarations are
rejected by recent pytest releases).
"""


def pytest_configure(config):
    config.addinivalue_line("markers", "notebook: notebook structural validation")
    config.addinivalue_line("markers", "slow: slow-running notebook execution tests")
