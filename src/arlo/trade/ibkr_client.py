import threading
import time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

from arlo.config import ForecastExConfig


class IBConnection(EWrapper, EClient):
    """Combined EWrapper+EClient that collects responses via callbacks."""

    def __init__(self):
        EClient.__init__(self, self)
        self._next_req_id = 1000
        self._next_order_id = 0
        self._results = {}
        self._events = {}
        self._connected_event = threading.Event()

    def next_id(self):
        rid = self._next_req_id
        self._next_req_id += 1
        self._events[rid] = threading.Event()
        self._results[rid] = []
        return rid

    def wait(self, rid, timeout=10):
        self._events[rid].wait(timeout)
        return self._results.pop(rid, [])

    # -- Connection callbacks --

    def nextValidId(self, orderId):
        self._next_order_id = orderId
        self._connected_event.set()

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        # Filter out informational messages
        if errorCode not in (2104, 2106, 2158):
            from arlo.shared.display import print_error

            print_error(f"IB [{errorCode}]: {errorString}")

    # -- Account callbacks --

    def accountSummary(self, reqId, account, tag, value, currency):
        self._results.setdefault(reqId, []).append(
            {"account": account, "tag": tag, "value": value, "currency": currency}
        )

    def accountSummaryEnd(self, reqId):
        if reqId in self._events:
            self._events[reqId].set()

    # -- Position callbacks --

    def position(self, account, contract, pos, avgCost):
        self._results.setdefault("positions", []).append(
            {
                "account": account,
                "symbol": contract.symbol,
                "secType": contract.secType,
                "exchange": contract.exchange,
                "right": contract.right,
                "strike": contract.strike,
                "expiry": contract.lastTradeDateOrContractMonth,
                "pos": pos,
                "avgCost": avgCost,
            }
        )

    def positionEnd(self):
        evt = self._events.get("positions_done")
        if evt:
            evt.set()

    # -- Order callbacks --

    def openOrder(self, orderId, contract, order, orderState):
        self._results.setdefault("orders", []).append(
            {
                "orderId": orderId,
                "symbol": contract.symbol,
                "right": contract.right,
                "strike": contract.strike,
                "action": order.action,
                "qty": int(order.totalQuantity),
                "price": order.lmtPrice,
                "status": orderState.status,
            }
        )

    def openOrderEnd(self):
        evt = self._events.get("orders_done")
        if evt:
            evt.set()

    def orderStatus(self, orderId, status, filled, remaining, *args):
        pass


def connect(cfg: ForecastExConfig = None) -> IBConnection:
    """Connect to TWS/IB Gateway and return the connection."""
    cfg = cfg or ForecastExConfig()
    conn = IBConnection()
    conn.connect(cfg.tws_host, cfg.tws_port, cfg.client_id)
    thread = threading.Thread(target=conn.run, daemon=True)
    thread.start()
    if not conn._connected_event.wait(timeout=5):
        raise ConnectionError("Timed out connecting to TWS/IB Gateway")
    return conn


def make_fx_contract(symbol, expiry, strike, right="C"):
    """Build a ForecastEx options contract.

    Args:
        symbol: Contract symbol (e.g. "GCE", "CPI", "FEDFUNDS")
        expiry: Expiration date as YYYYMMDD string
        strike: Strike price
        right: "C" for Yes, "P" for No
    """
    c = Contract()
    c.symbol = symbol
    c.secType = "OPT"
    c.currency = "USD"
    c.exchange = "FORECASTEX"
    c.lastTradeDateOrContractMonth = expiry
    c.right = right
    c.strike = float(strike)
    return c


def make_fx_order(quantity, price, tif="GTC"):
    """Build a ForecastEx limit buy order.

    ForecastEx only allows BUY orders with LMT type.
    To exit a position, buy the opposing contract (C<->P).
    """
    o = Order()
    o.action = "BUY"
    o.orderType = "LMT"
    o.totalQuantity = int(quantity)
    o.lmtPrice = float(price)
    o.tif = tif
    return o


def get_balance(conn: IBConnection):
    """Request account balance."""
    rid = conn.next_id()
    conn.reqAccountSummary(rid, "All", "TotalCashValue")
    return conn.wait(rid)


def get_positions(conn: IBConnection):
    """Request all positions, filtered to FORECASTEX exchange."""
    conn._results["positions"] = []
    conn._events["positions_done"] = threading.Event()
    conn.reqPositions()
    conn._events["positions_done"].wait(timeout=10)
    return [
        p
        for p in conn._results.get("positions", [])
        if p.get("exchange") == "FORECASTEX" or p.get("secType") == "OPT"
    ]


def get_orders(conn: IBConnection):
    """Request all open orders."""
    conn._results["orders"] = []
    conn._events["orders_done"] = threading.Event()
    conn.reqAllOpenOrders()
    conn._events["orders_done"].wait(timeout=10)
    return conn._results.get("orders", [])


def place_order(conn: IBConnection, contract, order):
    """Place an order and return the order ID."""
    order_id = conn._next_order_id
    conn._next_order_id += 1
    conn.placeOrder(order_id, contract, order)
    time.sleep(1)  # Brief wait for acknowledgment
    return order_id


def cancel_order(conn: IBConnection, order_id: int):
    """Cancel an order by ID."""
    from ibapi.order import OrderCancel

    conn.cancelOrder(order_id, OrderCancel())
