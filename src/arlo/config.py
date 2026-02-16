import os


class KalshiConfig:
    """Loads Kalshi credentials from environment."""

    @property
    def api_key_id(self) -> str:
        return os.environ["KALSHI_API_KEY_ID"]

    @property
    def private_key_path(self) -> str:
        return os.environ["KALSHI_PRIVATE_KEY_PATH"]

    @property
    def private_key_pem(self) -> str:
        with open(self.private_key_path) as f:
            return f.read()

    @property
    def host(self) -> str:
        return os.environ.get(
            "KALSHI_API_HOST",
            "https://api.elections.kalshi.com/trade-api/v2",
        )

    @property
    def is_demo(self) -> bool:
        return "demo" in self.host


class ForecastExConfig:
    """Loads IB/ForecastEx settings from environment."""

    @property
    def tws_host(self) -> str:
        return os.environ.get("IB_TWS_HOST", "127.0.0.1")

    @property
    def tws_port(self) -> int:
        return int(os.environ.get("IB_TWS_PORT", "7497"))

    @property
    def client_id(self) -> int:
        return int(os.environ.get("IB_CLIENT_ID", "1"))
