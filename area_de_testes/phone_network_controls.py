"""
Modulo de Controles Avancados de Rede (Wi-Fi e Bluetooth) do Conexao Movel.
Modelos de dados, normalizadores, sanitizadores e validadores de comandos.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class BtDeviceCategory(str, Enum):
    """Categorias padronizadas de dispositivos Bluetooth."""
    AUDIO = "audio"
    INPUT = "input"
    WATCH = "watch"
    PHONE = "phone"
    OTHER = "other"

    @classmethod
    def valid_categories(cls) -> Set[str]:
        return {item.value for item in cls}

    @classmethod
    def parse(cls, category: Any) -> BtDeviceCategory:
        if isinstance(category, cls):
            return category
        if not isinstance(category, (str, bytes)):
            raise ValueError(f"Categoria invalida: {type(category).__name__}")
        cat_str = (str(category, "utf-8") if isinstance(category, bytes) else str(category)).strip().lower()
        if not cat_str:
            return cls.OTHER
        aliases = {
            "headset": cls.AUDIO.value, "headphones": cls.AUDIO.value, "speaker": cls.AUDIO.value,
            "earphone": cls.AUDIO.value, "earphones": cls.AUDIO.value, "soundbar": cls.AUDIO.value,
            "audio_video": cls.AUDIO.value, "mouse": cls.INPUT.value, "keyboard": cls.INPUT.value,
            "gamepad": cls.INPUT.value, "joystick": cls.INPUT.value, "controller": cls.INPUT.value,
            "touchpad": cls.INPUT.value, "pointer": cls.INPUT.value, "teclado/controle": cls.INPUT.value,
            "teclado": cls.INPUT.value, "controle": cls.INPUT.value, "periferico": cls.INPUT.value,
            "smartwatch": cls.WATCH.value, "wearable": cls.WATCH.value, "band": cls.WATCH.value,
            "relogio": cls.WATCH.value, "relógio": cls.WATCH.value, "pulseira": cls.WATCH.value,
            "smartphone": cls.PHONE.value, "mobile": cls.PHONE.value, "celular": cls.PHONE.value,
            "telefone": cls.PHONE.value, "tablet": cls.PHONE.value, "computer": cls.OTHER.value,
            "computador": cls.OTHER.value, "pc": cls.OTHER.value, "laptop": cls.OTHER.value,
            "desktop": cls.OTHER.value, "printer": cls.OTHER.value, "unknown": cls.OTHER.value,
            "outro": cls.OTHER.value, "outros": cls.OTHER.value,
        }
        normalized = aliases.get(cat_str, cat_str)
        for member in cls:
            if member.value == normalized:
                return member
        return cls.OTHER

    @classmethod
    def is_valid(cls, category: Any) -> bool:
        try:
            cls.parse(category)
            return True
        except ValueError:
            return False


_MAC_PATTERN = re.compile(r"^(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$|^[0-9a-fA-F]{12}$")


def validate_mac(mac: Any) -> bool:
    """Verifica se uma string representa um endereco MAC valido."""
    return bool(isinstance(mac, str) and _MAC_PATTERN.match(mac.strip()))


def normalize_mac(mac: Any) -> str:
    """Normaliza um endereco MAC para XX:XX:XX:XX:XX:XX em maiusculas."""
    if not isinstance(mac, str):
        raise ValueError(f"Endereco MAC deve ser string, recebido {type(mac).__name__}")
    mac_clean = mac.strip()
    if not _MAC_PATTERN.match(mac_clean):
        raise ValueError(f"Endereco MAC invalido: '{mac}'")
    raw = mac_clean.replace(":", "").replace("-", "").upper()
    return ":".join(raw[i:i + 2] for i in range(0, 12, 2))


def sanitize_wifi_ssid(ssid: Any) -> Optional[str]:
    """Sanitiza o SSID de uma rede Wi-Fi, removendo aspas e identificadores nulos."""
    if ssid is None:
        return None
    cleaned = (str(ssid) if not isinstance(ssid, str) else ssid).strip()
    while (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        if len(cleaned) <= 1:
            return None
        cleaned = cleaned[1:-1].strip()
    if cleaned.startswith(r'\"') and cleaned.endswith(r'\"'):
        cleaned = cleaned[2:-2].strip()
    if cleaned.lower() in {"", "<unknown ssid>", "<unknown>", "unknown", "0x", "none", "null"}:
        return None
    return cleaned


def clamp_and_normalize_wifi_signal(signal: Any) -> Optional[int]:
    """Normaliza o sinal Wi-Fi para o intervalo [0, 100], suportando dBm e percentual."""
    if signal is None:
        return None
    if isinstance(signal, str):
        try:
            signal = float(signal.strip())
        except ValueError:
            raise ValueError(f"Nivel de sinal Wi-Fi invalido: '{signal}'")
    if not isinstance(signal, (int, float)):
        raise ValueError(f"Sinal deve ser numerico, recebido {type(signal).__name__}")
    if signal < 0:
        signal = 2 * (signal + 100)
    return max(0, min(100, int(round(signal))))


class BtDeviceInfo:
    """Informacoes de um dispositivo Bluetooth pareado ou conectado."""
    def __init__(
        self,
        mac: str,
        name: str,
        category: Union[BtDeviceCategory, str] = BtDeviceCategory.OTHER,
        is_connected: bool = False,
        is_paired: bool = True,
        battery_level: Optional[int] = None,
    ):
        self.mac = normalize_mac(mac)
        self.name = str(name).strip() if name else "Dispositivo Bluetooth"
        self.category = BtDeviceCategory.parse(category)
        self.is_connected = bool(is_connected)
        self.is_paired = bool(is_paired)
        self.battery_level = max(0, min(100, int(battery_level))) if battery_level is not None else None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "mac": self.mac, "name": self.name, "category": self.category.value,
            "is_connected": self.is_connected, "is_paired": self.is_paired,
        }
        if self.battery_level is not None:
            data["battery_level"] = self.battery_level
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BtDeviceInfo:
        if not isinstance(data, dict):
            raise ValueError(f"Esperado dicionario para BtDeviceInfo, recebido {type(data).__name__}")
        return cls(
            mac=data.get("mac", ""), name=data.get("name", ""),
            category=data.get("category", BtDeviceCategory.OTHER.value),
            is_connected=data.get("is_connected", False),
            is_paired=data.get("is_paired", True),
            battery_level=data.get("battery_level"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> BtDeviceInfo:
        return cls.from_dict(json.loads(json_str))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BtDeviceInfo):
            return False
        return (
            self.mac == other.mac and self.name == other.name and self.category == other.category
            and self.is_connected == other.is_connected and self.is_paired == other.is_paired
            and self.battery_level == other.battery_level
        )


class WifiNetworkInfo:
    """Informacoes de uma rede Wi-Fi detectada ou conectada."""
    def __init__(
        self,
        ssid: Optional[str],
        signal: Any = 0,
        bssid: Optional[str] = None,
        security: str = "WPA2",
        is_connected: bool = False,
        is_saved: bool = False,
        frequency: Optional[int] = None,
    ):
        self.ssid = sanitize_wifi_ssid(ssid)
        self.signal = clamp_and_normalize_wifi_signal(signal) or 0
        self.bssid = normalize_mac(bssid) if (bssid and validate_mac(bssid)) else None
        self.security = str(security).strip().upper() if security else "OPEN"
        self.is_connected = bool(is_connected)
        self.is_saved = bool(is_saved)
        self.frequency = int(frequency) if frequency is not None else None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "ssid": self.ssid, "signal": self.signal, "security": self.security,
            "is_connected": self.is_connected, "is_saved": self.is_saved,
        }
        if self.bssid is not None:
            data["bssid"] = self.bssid
        if self.frequency is not None:
            data["frequency"] = self.frequency
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WifiNetworkInfo:
        if not isinstance(data, dict):
            raise ValueError(f"Esperado dicionario para WifiNetworkInfo, recebido {type(data).__name__}")
        return cls(
            ssid=data.get("ssid"), signal=data.get("signal", 0), bssid=data.get("bssid"),
            security=data.get("security", "WPA2"), is_connected=data.get("is_connected", False),
            is_saved=data.get("is_saved", False), frequency=data.get("frequency"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> WifiNetworkInfo:
        return cls.from_dict(json.loads(json_str))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, WifiNetworkInfo):
            return False
        return (
            self.ssid == other.ssid and self.signal == other.signal and self.bssid == other.bssid
            and self.security == other.security and self.is_connected == other.is_connected
            and self.is_saved == other.is_saved and self.frequency == other.frequency
        )


class PhoneToggles:
    """Estado de configuracoes rapidas do smartphone (protocolo v0 expandido)."""
    VALID_RINGER_MODES = {"ring", "vibrate", "silent"}

    def __init__(
        self,
        dnd: bool = False,
        ringer: str = "ring",
        flashlight: Optional[bool] = None,
        volume: int = 0,
        brightness: int = 0,
        wifi: bool = False,
        bluetooth: bool = False,
        wifi_ssid: Optional[str] = None,
        wifi_signal: Optional[Any] = None,
        wifi_networks: Optional[List[Union[WifiNetworkInfo, Dict[str, Any]]]] = None,
        bt_devices: Optional[List[Union[BtDeviceInfo, Dict[str, Any]]]] = None,
    ):
        self.dnd = bool(dnd)
        self.ringer = ringer if ringer in self.VALID_RINGER_MODES else "ring"
        self.flashlight = bool(flashlight) if flashlight is not None else None
        self.volume = max(0, min(100, int(volume)))
        self.brightness = max(0, min(100, int(brightness)))
        self.wifi = bool(wifi)
        self.bluetooth = bool(bluetooth)
        self.wifi_ssid = sanitize_wifi_ssid(wifi_ssid)
        self.wifi_signal = clamp_and_normalize_wifi_signal(wifi_signal)

        self.wifi_networks: List[WifiNetworkInfo] = []
        if wifi_networks:
            for net in wifi_networks:
                if isinstance(net, WifiNetworkInfo):
                    self.wifi_networks.append(net)
                elif isinstance(net, dict):
                    self.wifi_networks.append(WifiNetworkInfo.from_dict(net))

        self.bt_devices: List[BtDeviceInfo] = []
        if bt_devices:
            for dev in bt_devices:
                if isinstance(dev, BtDeviceInfo):
                    self.bt_devices.append(dev)
                elif isinstance(dev, dict):
                    self.bt_devices.append(BtDeviceInfo.from_dict(dev))

    def is_valid(self) -> bool:
        return (
            self.ringer in self.VALID_RINGER_MODES
            and 0 <= self.volume <= 100
            and 0 <= self.brightness <= 100
            and (self.wifi_signal is None or 0 <= self.wifi_signal <= 100)
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "dnd": self.dnd, "ringer": self.ringer, "volume": self.volume,
            "brightness": self.brightness, "wifi": self.wifi, "bluetooth": self.bluetooth,
        }
        if self.flashlight is not None:
            data["flashlight"] = self.flashlight
        if self.wifi_ssid is not None:
            data["wifi_ssid"] = self.wifi_ssid
        if self.wifi_signal is not None:
            data["wifi_signal"] = self.wifi_signal
        if self.wifi_networks:
            data["wifi_networks"] = [net.to_dict() for net in self.wifi_networks]
        if self.bt_devices:
            data["bt_devices"] = [dev.to_dict() for dev in self.bt_devices]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhoneToggles:
        if not isinstance(data, dict):
            raise ValueError(f"Esperado dicionario para PhoneToggles, recebido {type(data).__name__}")
        return cls(
            dnd=data.get("dnd", False), ringer=data.get("ringer", "ring"),
            flashlight=data.get("flashlight"), volume=data.get("volume", 0),
            brightness=data.get("brightness", 0), wifi=data.get("wifi", False),
            bluetooth=data.get("bluetooth", False), wifi_ssid=data.get("wifi_ssid"),
            wifi_signal=data.get("wifi_signal"), wifi_networks=data.get("wifi_networks"),
            bt_devices=data.get("bt_devices"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> PhoneToggles:
        return cls.from_dict(json.loads(json_str))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PhoneToggles):
            return False
        return (
            self.dnd == other.dnd and self.ringer == other.ringer and self.flashlight == other.flashlight
            and self.volume == other.volume and self.brightness == other.brightness
            and self.wifi == other.wifi and self.bluetooth == other.bluetooth
            and self.wifi_ssid == other.wifi_ssid and self.wifi_signal == other.wifi_signal
            and self.wifi_networks == other.wifi_networks and self.bt_devices == other.bt_devices
        )


def create_wifi_scan_command() -> Dict[str, Any]:
    """Cria o payload para solicitacao de varredura de redes Wi-Fi."""
    return {"id": "wifi_scan", "action": "scan", "target": "wifi"}


def create_wifi_connect_command(
    ssid: str, password: Optional[str] = None, bssid: Optional[str] = None, hidden: bool = False
) -> Dict[str, Any]:
    """Cria o payload para conexao a uma rede Wi-Fi especifica."""
    clean_ssid = sanitize_wifi_ssid(ssid)
    if not clean_ssid:
        raise ValueError(f"SSID de conexao Wi-Fi invalido ou ausente: '{ssid}'")
    payload: Dict[str, Any] = {
        "id": "wifi_connect", "action": "connect", "target": "wifi",
        "ssid": clean_ssid, "hidden": bool(hidden),
    }
    if password is not None:
        payload["password"] = str(password)
    if bssid:
        payload["bssid"] = normalize_mac(bssid)
    return payload


def create_bt_connect_command(mac: str) -> Dict[str, Any]:
    """Cria o payload para conexao a um dispositivo Bluetooth pareado."""
    return {"id": "bt_connect", "action": "connect", "target": "bluetooth", "mac": normalize_mac(mac)}


def create_bt_disconnect_command(mac: str) -> Dict[str, Any]:
    """Cria o payload para desconexao de um dispositivo Bluetooth conectado."""
    return {"id": "bt_disconnect", "action": "disconnect", "target": "bluetooth", "mac": normalize_mac(mac)}


def validate_network_command(payload: Dict[str, Any]) -> bool:
    """Valida a conformidade de um payload de comando de rede."""
    if not isinstance(payload, dict):
        return False
    cmd_id = payload.get("id")
    target = payload.get("target")
    action = payload.get("action")
    if cmd_id == "wifi_scan":
        return target == "wifi" and action == "scan"
    if cmd_id == "wifi_connect":
        if target != "wifi" or action != "connect":
            return False
        ssid = payload.get("ssid")
        if not ssid or not sanitize_wifi_ssid(ssid):
            return False
        bssid = payload.get("bssid")
        return not bssid or validate_mac(bssid)
    if cmd_id in ("bt_connect", "bt_disconnect"):
        expected_action = "connect" if cmd_id == "bt_connect" else "disconnect"
        if target != "bluetooth" or action != expected_action:
            return False
        mac = payload.get("mac")
        return bool(mac and validate_mac(mac))
    return False
