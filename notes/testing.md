# Testing

- Home Assistant's test plugin needs Linux (`fcntl`), so tests run in WSL (Ubuntu), not Windows.
- WSL Ubuntu has no `pip`/`venv` package and no sudo, so `uv` is used: a Linux `uv` binary in
  `~/.local/bin/uv` (taken from the `uv` wheel on PyPI). Venv: `~/.venvs/esp-spa-ha` (Python 3.14),
  with `pytest-homeassistant-custom-component` (HA 2026.10.4 at the time of v1).
- Recreate: `~/.local/bin/uv venv ~/.venvs/esp-spa-ha --python 3.14` then
  `~/.local/bin/uv pip install --python ~/.venvs/esp-spa-ha/bin/python -r requirements_test.txt`.
- Don't use Docker Desktop on this machine (owner: not working correctly).
- The tests mock the module with `aioclient_mock` (`tests/conftest.py`); change the `status` fixture
  and call `entry.runtime_data.async_refresh()` to simulate the spa.
- Real-hardware test: waits for the install at the owners' house (firmware repo roadmap).
