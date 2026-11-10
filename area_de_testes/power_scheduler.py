"""
Módulo de Gerenciamento de Energia e Agendador (Power Scheduler) do NectarLink.
Suporta ações de energia expandidas, agendamentos recorrentes e Wake-on-LAN.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class PowerAction(str, Enum):
    """
    Ações de energia suportadas pelo NectarLink.
    Expandidas para incluir lock, sleep, shutdown e reboot.
    """
    LOCK = "lock"
    SLEEP = "sleep"
    SHUTDOWN = "shutdown"
    REBOOT = "reboot"

    @classmethod
    def valid_actions(cls) -> Set[str]:
        return {item.value for item in cls}

    @classmethod
    def parse(cls, action: Any) -> PowerAction:
        """
        Normaliza e converte uma string de ação em PowerAction.
        Suporta sinônimos comuns (ex.: poweroff, suspend, restart).
        Lança ValueError se a ação for inválida.
        """
        if isinstance(action, cls):
            return action

        if not isinstance(action, (str, bytes)):
            raise ValueError(f"Ação de energia deve ser string ou PowerAction, recebido {type(action).__name__}")
        
        act_str = str(action, encoding="utf-8") if isinstance(action, bytes) else str(action)
        act_str = act_str.strip().lower()
        if not act_str:
            raise ValueError("Ação de energia não pode ser vazia")

        aliases = {
            "suspend": cls.SLEEP.value,
            "poweroff": cls.SHUTDOWN.value,
            "power_off": cls.SHUTDOWN.value,
            "restart": cls.REBOOT.value,
        }
        normalized = aliases.get(act_str, act_str)

        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member

        valid_list = sorted(list(cls.valid_actions()))
        raise ValueError(f"Ação de energia inválida: '{action}'. Ações permitidas: {valid_list}")

    @classmethod
    def is_valid(cls, action: Any) -> bool:
        """Retorna True se a ação for válida, False caso contrário."""
        try:
            cls.parse(action)
            return True
        except ValueError:
            return False


# Mapeamento padrão de dias da semana (0 = Segunda-feira, 6 = Domingo, conforme datetime.weekday())
DAY_NAMES_EN = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES_PT = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

DAY_NAME_TO_INT = {
    "mon": 0, "monday": 0, "seg": 0, "segunda": 0, "segunda-feira": 0,
    "tue": 1, "tuesday": 1, "ter": 1, "terca": 1, "terça": 1, "terça-feira": 1,
    "wed": 2, "wednesday": 2, "qua": 2, "quarta": 2, "quarta-feira": 2,
    "thu": 3, "thursday": 3, "qui": 3, "quinta": 3, "quinta-feira": 3,
    "fri": 4, "friday": 4, "sex": 4, "sexta": 4, "sexta-feira": 4,
    "sat": 5, "saturday": 5, "sab": 5, "sabado": 5, "sábado": 5,
    "sun": 6, "sunday": 6, "dom": 6, "domingo": 6,
}

WEEKDAYS_SET = {0, 1, 2, 3, 4}  # Segunda a Sexta
WEEKEND_SET = {5, 6}            # Sábado e Domingo
ALL_DAYS_SET = {0, 1, 2, 3, 4, 5, 6}


def normalize_days(days: Union[List[Union[int, str]], Set[Union[int, str]], str]) -> List[int]:
    """
    Normaliza representações de dias da semana para uma lista ordenada de inteiros (0=Segunda ... 6=Domingo).
    """
    if isinstance(days, str):
        days_list = [d.strip() for d in days.split(",") if d.strip()]
    elif hasattr(days, "__iter__"):
        days_list = list(days)
    else:
        raise ValueError(f"Formato inválido para dias: {days}")

    normalized: Set[int] = set()
    for day in days_list:
        if isinstance(day, int):
            if not 0 <= day <= 6:
                raise ValueError(f"Dia da semana numérico fora do intervalo [0-6]: {day}")
            normalized.add(day)
        elif isinstance(day, str):
            clean = day.strip().lower()
            if clean in DAY_NAME_TO_INT:
                normalized.add(DAY_NAME_TO_INT[clean])
            elif clean.isdigit():
                val = int(clean)
                if not 0 <= val <= 6:
                    raise ValueError(f"Dia da semana numérico fora do intervalo [0-6]: {val}")
                normalized.add(val)
            else:
                raise ValueError(f"Dia da semana desconhecido: '{day}'")
        else:
            raise ValueError(f"Tipo inválido para dia da semana: {type(day).__name__}")

    return sorted(list(normalized))


class PowerSchedule:
    """
    Representação de uma regra de agendamento de energia no NectarLink.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        action: Union[PowerAction, str] = PowerAction.LOCK,
        hour: int = 0,
        minute: int = 0,
        days: Optional[Union[List[Union[int, str]], Set[Union[int, str]], str]] = None,
        enabled: bool = True,
        name: str = "",
        notify_before: bool = True,
        warning_seconds: int = 60,
        force: bool = False,
        repeat: bool = True,
        one_shot: bool = False,
    ):
        self.id = str(id or uuid.uuid4())
        self.name = str(name or "")
        self.action = PowerAction.parse(action).value

        if not isinstance(hour, int) or not (0 <= hour <= 23):
            raise ValueError(f"Hora inválida: {hour}. Deve estar entre 0 e 23.")
        if not isinstance(minute, int) or not (0 <= minute <= 59):
            raise ValueError(f"Minuto inválido: {minute}. Deve estar entre 0 e 59.")
        self.hour = hour
        self.minute = minute

        # Se days for None e não for one-shot, assume todos os dias
        if days is None:
            self.days = list(range(7))
        else:
            norm = normalize_days(days)
            if not norm and not one_shot:
                raise ValueError("A lista de dias de agendamento recorrente não pode ser vazia.")
            self.days = norm

        # Flags
        if not isinstance(enabled, bool):
            raise TypeError("Flag 'enabled' deve ser booleana")
        if not isinstance(notify_before, bool):
            raise TypeError("Flag 'notify_before' deve ser booleana")
        if not isinstance(force, bool):
            raise TypeError("Flag 'force' deve ser booleana")
        if not isinstance(repeat, bool):
            raise TypeError("Flag 'repeat' deve ser booleana")
        if not isinstance(one_shot, bool):
            raise TypeError("Flag 'one_shot' deve ser booleana")
        if not isinstance(warning_seconds, int) or warning_seconds < 0:
            raise ValueError("Flag 'warning_seconds' deve ser um inteiro não-negativo")

        self.enabled = enabled
        self.notify_before = notify_before
        self.warning_seconds = warning_seconds
        self.force = force
        self.repeat = repeat
        self.one_shot = one_shot

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a configuração para dicionário com campos estritamente tipados."""
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action,
            "hour": self.hour,
            "minute": self.minute,
            "days": list(self.days),
            "enabled": self.enabled,
            "notify_before": self.notify_before,
            "warning_seconds": self.warning_seconds,
            "force": self.force,
            "repeat": self.repeat,
            "one_shot": self.one_shot,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializa a configuração para string JSON formatada."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PowerSchedule:
        """Desserializa e valida a partir de um dicionário."""
        if not isinstance(data, dict):
            raise TypeError(f"Esperado dicionário para PowerSchedule, recebido {type(data).__name__}")

        required_keys = {"action", "hour", "minute"}
        missing = required_keys - set(data.keys())
        if missing:
            raise KeyError(f"Campos obrigatórios ausentes no PowerSchedule: {sorted(list(missing))}")

        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            action=data["action"],
            hour=data["hour"],
            minute=data["minute"],
            days=data.get("days"),
            enabled=data.get("enabled", True),
            notify_before=data.get("notify_before", True),
            warning_seconds=data.get("warning_seconds", 60),
            force=data.get("force", False),
            repeat=data.get("repeat", True),
            one_shot=data.get("one_shot", False),
        )

    @classmethod
    def from_json(cls, json_str: str) -> PowerSchedule:
        """Desserializa e valida a partir de uma string JSON."""
        if not isinstance(json_str, str):
            raise TypeError(f"Esperada string JSON, recebido {type(json_str).__name__}")
        parsed = json.loads(json_str)
        return cls.from_dict(parsed)

    def next_trigger(self, base_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calcula o próximo disparo relativo a base_time."""
        return calculate_next_trigger(self, base_time=base_time)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PowerSchedule):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.action == other.action
            and self.hour == other.hour
            and self.minute == other.minute
            and sorted(self.days) == sorted(other.days)
            and self.enabled == other.enabled
            and self.notify_before == other.notify_before
            and self.warning_seconds == other.warning_seconds
            and self.force == other.force
            and self.repeat == other.repeat
            and self.one_shot == other.one_shot
        )

    def __repr__(self) -> str:
        return (
            f"PowerSchedule(id={self.id!r}, action={self.action!r}, "
            f"time={self.hour:02d}:{self.minute:02d}, days={self.days}, enabled={self.enabled})"
        )


def calculate_next_trigger(
    schedule: PowerSchedule,
    base_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """
    Calcula a data e hora do próximo disparo (next_trigger) de um agendamento.

    Regras aplicadas:
    - Se schedule.enabled for False, retorna None.
    - Se schedule.days for vazio e não for one-shot, retorna None.
    - Avalia a partir do instante base_time (datetime.now() por padrão).
    - Se o horário no mesmo dia já tiver passado (candidate <= base_time),
      o próximo disparo obrigatoriamente será em um dia futuro correspondente.
    - Se hoje estiver na lista de dias e o horário for estritamente futuro, dispara hoje.
    - Respeita os dias selecionados (ex.: Seg-Sex vs Fim de Semana).
    - Trata corretamente viradas de dia, mês e ano.
    """
    if not schedule.enabled:
        return None

    if not schedule.days and not schedule.one_shot:
        return None

    now = base_time or datetime.now()
    target_days = set(schedule.days)

    # Verifica os próximos 14 dias para cobrir semanas completas e edge cases
    for day_offset in range(0, 15):
        candidate_date = (now + timedelta(days=day_offset)).date()
        candidate_weekday = candidate_date.weekday()

        if candidate_weekday in target_days:
            candidate_dt = datetime.combine(
                candidate_date,
                time(hour=schedule.hour, minute=schedule.minute, second=0, microsecond=0)
            )
            # O disparo precisa ser estritamente no futuro de now
            if candidate_dt > now:
                return candidate_dt

    return None


# ==============================================================================
# Wake-on-LAN (WOL) e Validação de Pacotes Mágicos
# ==============================================================================

WOL_MAGIC_PACKET_LENGTH = 102
WOL_HEADER = b"\xff" * 6
WOL_REPETITIONS = 16


def parse_mac(mac: Union[str, bytes]) -> bytes:
    """
    Analisa e valida um endereço MAC de 6 octetos.
    Aceita separadores como ':' ou '-' ou strings hex contínuas.
    Rejeita endereços nulos (00:00:00:00:00:00), broadcast (FF:FF:FF:FF:FF:FF)
    e endereços multicast (bit 0 do primeiro octeto = 1).
    """
    if isinstance(mac, (bytes, bytearray)):
        if len(mac) != 6:
            raise ValueError(f"Tamanho de MAC em bytes deve ser 6, recebido {len(mac)}")
        raw = bytes(mac)
    elif isinstance(mac, str):
        cleaned = re.sub(r"[:-]", "", mac.strip())
        if len(cleaned) != 12:
            raise ValueError(f"MAC address inválido '{mac}': esperado 12 caracteres hexadecimais")
        try:
            raw = bytes.fromhex(cleaned)
        except ValueError as e:
            raise ValueError(f"MAC address contém caracteres não hexadecimais '{mac}': {e}")
    else:
        raise TypeError(f"Endereço MAC deve ser str ou bytes, recebido {type(mac).__name__}")

    if raw == b"\x00" * 6:
        raise ValueError("Endereço MAC inválido: endereço nulo (00:00:00:00:00:00) não permitido")

    if raw == b"\xff" * 6:
        raise ValueError("Endereço MAC inválido: endereço broadcast (FF:FF:FF:FF:FF:FF) não permitido")

    # Multicast: bit menos significativo do primeiro octeto setado (raw[0] & 1 == 1)
    if raw[0] & 0x01 == 1:
        raise ValueError("Endereço MAC inválido: endereço multicast não permitido para Wake-on-LAN")

    return raw


def format_mac(mac_bytes: bytes) -> str:
    """Formata 6 bytes de MAC no padrão 'aa:bb:cc:dd:ee:ff'."""
    if len(mac_bytes) != 6:
        raise ValueError("Esperado exatamente 6 bytes para formatar MAC")
    return ":".join(f"{b:02x}" for b in mac_bytes)


def create_magic_packet(mac: Union[str, bytes]) -> bytes:
    """
    Gera o Magic Packet padrão Wake-on-LAN de 102 bytes:
    6 bytes de 0xFF seguidos pelo MAC de 6 bytes repetido 16 vezes.
    """
    mac_bytes = parse_mac(mac)
    packet = WOL_HEADER + (mac_bytes * WOL_REPETITIONS)
    assert len(packet) == WOL_MAGIC_PACKET_LENGTH, f"Tamanho incorreto do pacote: {len(packet)}"
    return packet


def validate_magic_packet(
    packet: bytes,
    expected_mac: Optional[Union[str, bytes]] = None,
) -> bool:
    """
    Valida um pacote Wake-on-LAN Magic Packet:
    - Deve possuir exatamente 102 bytes
    - Primeiros 6 bytes devem ser 0xFF
    - Próximos 96 bytes devem ser exatamente 16 repetições do mesmo MAC
    - O MAC extraído deve ser unicast válido
    - Se expected_mac for fornecido, compara com o MAC do pacote
    """
    if not isinstance(packet, (bytes, bytearray)):
        return False

    if len(packet) != WOL_MAGIC_PACKET_LENGTH:
        return False

    if packet[:6] != WOL_HEADER:
        return False

    extracted_mac = packet[6:12]

    # Verifica se os 96 bytes restantes são repetições idênticas do extracted_mac
    expected_body = extracted_mac * WOL_REPETITIONS
    if packet[6:] != expected_body:
        return False

    # Valida o MAC extraído com as regras de unicast/não-nulo
    try:
        parse_mac(extracted_mac)
    except ValueError:
        return False

    if expected_mac is not None:
        try:
            expected_bytes = parse_mac(expected_mac)
            if extracted_mac != expected_bytes:
                return False
        except (ValueError, TypeError):
            return False

    return True
