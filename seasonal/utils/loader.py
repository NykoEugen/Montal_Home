from __future__ import annotations

import inspect
import logging
from importlib import import_module
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = ["PackImportError", "load_pack"]


class PackImportError(RuntimeError):
    """Raised when a pack cannot be imported safely."""


def load_pack(pack_path: str) -> Pack:
    if not pack_path or not pack_path.strip():
        raise PackImportError("Pack path must be a non-empty string.")

    module_ref, attr_ref = _split_pack_reference(pack_path)
    normalized = _normalize_module_path(module_ref)

    try:
        module = import_module(normalized)
    except Exception as exc:
        logger.exception("Unexpected error importing pack module %s", normalized)
        raise PackImportError(f"Failed to import pack module {normalized}") from exc

    pack = _materialize_pack(module, attr_ref)
    if not isinstance(pack, Pack):
        raise PackImportError(f"Module {normalized} did not return a Pack instance.")

    return pack


def _normalize_module_path(module_path: str) -> str:
    candidate = module_path.strip().replace("/", ".")
    parts = [part for part in candidate.split(".") if part]
    if not parts:
        raise PackImportError("Invalid pack path supplied.")
    return ".".join(parts)


def _materialize_pack(module, attr_ref: Optional[str]) -> Pack:
    if attr_ref:
        target = getattr(module, attr_ref, None)
        if target is None:
            raise PackImportError(f"Attribute {attr_ref} not found in module {module.__name__}")
        if isinstance(target, Pack):
            return target
        if inspect.isclass(target) and issubclass(target, Pack):
            try:
                return target()
            except Exception as exc:  # pragma: no cover - defensive
                raise PackImportError(
                    f"Failed to instantiate Pack class {attr_ref} in {module.__name__}"
                ) from exc
        if callable(target):
            candidate = target()
            if isinstance(candidate, Pack):
                return candidate
        raise PackImportError(f"Attribute {attr_ref} in {module.__name__} is not a Pack.")

    if hasattr(module, "get_pack") and callable(module.get_pack):
        pack = module.get_pack()
        if isinstance(pack, Pack):
            return pack

    candidate = getattr(module, "pack", None)
    if isinstance(candidate, Pack):
        return candidate

    pack_class = getattr(module, "Pack", None)
    if inspect.isclass(pack_class) and issubclass(pack_class, Pack):
        try:
            return pack_class()
        except Exception as exc:  # pragma: no cover - defensive
            raise PackImportError(f"Failed to instantiate Pack class in {module.__name__}") from exc

    raise PackImportError(f"No Pack implementation found in module {module.__name__}")


def _split_pack_reference(pack_path: str) -> Tuple[str, Optional[str]]:
    if ":" not in pack_path:
        return pack_path, None
    module_ref, attr_ref = pack_path.split(":", 1)
    module_ref = module_ref.strip()
    attr_ref = attr_ref.strip()
    if not module_ref or not attr_ref:
        raise PackImportError("Pack path with attribute must include both module and attribute.")
    return module_ref, attr_ref


from seasonal.packs.base import Pack
