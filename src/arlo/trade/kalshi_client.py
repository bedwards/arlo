import uuid

from kalshi_python import Configuration, KalshiClient, CreateOrderRequest

from arlo.config import KalshiConfig


def get_client(cfg: KalshiConfig = None) -> KalshiClient:
    """Create an authenticated Kalshi client."""
    cfg = cfg or KalshiConfig()
    config = Configuration(host=cfg.host)
    config.api_key_id = cfg.api_key_id
    config.private_key_pem = cfg.private_key_pem
    return KalshiClient(config)


def get_balance(client: KalshiClient) -> int:
    """Returns balance in cents."""
    resp = client.get_balance()
    return resp.balance


def get_positions(client: KalshiClient, **kwargs):
    """Returns list of open positions."""
    resp = client.get_positions(**kwargs)
    return resp.market_positions


def get_markets(client: KalshiClient, **kwargs):
    """Returns list of markets."""
    resp = client.get_markets(**kwargs)
    return resp.markets


def get_market(client: KalshiClient, ticker: str):
    """Returns a single market by ticker."""
    resp = client.get_market(ticker)
    return resp.market


def get_orderbook(client: KalshiClient, ticker: str, depth: int = 10):
    """Returns orderbook for a market."""
    resp = client.get_market_orderbook(ticker, depth=depth)
    return resp


def get_orders(client: KalshiClient, **kwargs):
    """Returns list of orders."""
    resp = client.get_orders(**kwargs)
    return resp.orders


def create_order(client: KalshiClient, ticker, side, count, price, order_type="limit"):
    """Place an order. Price is in cents (1-99)."""
    req = CreateOrderRequest(
        ticker=ticker,
        action="buy",
        side=side,
        count=count,
        type=order_type,
        yes_price=price if side == "yes" else None,
        no_price=price if side == "no" else None,
        client_order_id=str(uuid.uuid4()),
    )
    resp = client.create_order(req)
    return resp.order


def cancel_order(client: KalshiClient, order_id: str):
    """Cancel an order by ID."""
    return client.cancel_order(order_id)
