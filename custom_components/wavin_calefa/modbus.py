"""Small Modbus TCP client for Wavin Calefa."""

from __future__ import annotations

from dataclasses import dataclass
import socket
import struct


class WavinCalefaError(Exception):
    """Base error for Wavin Calefa communication."""


class WavinCalefaConnectionError(WavinCalefaError):
    """Raised when the device cannot be reached."""


class WavinCalefaModbusError(WavinCalefaError):
    """Raised when the device returns a Modbus error."""


@dataclass(frozen=True)
class WavinCalefaClient:
    """Minimal synchronous Modbus TCP reader."""

    host: str
    port: int
    unit_id: int
    timeout: float = 3.0

    def _request(self, function_code: int, address: int, quantity: int = 1) -> bytes:
        transaction_id = (address + function_code * 10000) & 0xFFFF
        pdu = struct.pack(">BHH", function_code, address, quantity)
        mbap = struct.pack(">HHHB", transaction_id, 0, len(pdu) + 1, self.unit_id)
        request = mbap + pdu

        try:
            with socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            ) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(request)
                header = sock.recv(7)
                if len(header) != 7:
                    raise WavinCalefaConnectionError("Short Modbus TCP header")
                _, _, length, _ = struct.unpack(">HHHB", header)
                body = b""
                while len(body) < length - 1:
                    chunk = sock.recv(length - 1 - len(body))
                    if not chunk:
                        break
                    body += chunk
        except OSError as err:
            raise WavinCalefaConnectionError(str(err)) from err

        if not body:
            raise WavinCalefaConnectionError("Empty Modbus response")

        response_code = body[0]
        if response_code & 0x80:
            exception_code = body[1] if len(body) > 1 else 0
            raise WavinCalefaModbusError(
                f"Modbus exception {exception_code} at address {address}"
            )
        if response_code != function_code:
            raise WavinCalefaModbusError(
                f"Unexpected function code {response_code}, expected {function_code}"
            )
        return body

    def read_register(self, address: int, *, input_type: str = "input") -> int:
        """Read a single 16-bit register."""
        function_code = 4 if input_type == "input" else 3
        body = self._request(function_code, address, 1)
        byte_count = body[1]
        if byte_count < 2:
            raise WavinCalefaModbusError(f"No register data at address {address}")
        return struct.unpack(">H", body[2:4])[0]

    def read_discrete_input(self, address: int) -> bool:
        """Read a single discrete input."""
        body = self._request(2, address, 1)
        if body[1] < 1:
            raise WavinCalefaModbusError(f"No bit data at address {address}")
        return bool(body[2] & 1)


def signed16(value: int) -> int:
    """Convert unsigned 16-bit integer to signed integer."""
    return value - 65536 if value >= 32768 else value

