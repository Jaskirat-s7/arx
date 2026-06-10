"""
title: Structured diagnostic records for the PyArx public API.
summary: >-
  Define the stable, frozen Diagnostic record that PyArx exposes to callers
  and the helpers that translate upstream IRx structured diagnostics into it.
  The Diagnostic type is deliberately self-contained and never imports arx or
  irx at module load time, so importing pyarx.diagnostics stays free of the
  LLVM toolchain. Upstream records are read by attribute (duck-typed) so the
  same helper handles every IRx diagnostic-bearing object.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    """
    title: One structured diagnostic emitted by the Arx pipeline.
    attributes:
      message:
        type: str
        description: The human-readable diagnostic message.
      severity:
        type: str
        description: The severity label, e.g. "error" or "warning".
      line:
        type: int | None
        description: One-based source line, when known.
      col:
        type: int | None
        description: One-based source column, when known.
      end_line:
        type: int | None
        description: One-based end line of the span, when known.
      end_col:
        type: int | None
        description: One-based end column of the span, when known.
      code:
        type: str | None
        description: Stable diagnostic code, e.g. "S001", when known.
      phase:
        type: str | None
        description: Pipeline phase that produced the diagnostic.
      module_key:
        type: str | None
        description: Module attribution for the diagnostic, when known.
      hint:
        type: str | None
        description: Optional remediation hint.
      notes:
        type: tuple[str, ...]
        description: Optional supplementary notes.
    """

    message: str
    severity: str = "error"
    line: int | None = None
    col: int | None = None
    end_line: int | None = None
    end_col: int | None = None
    code: str | None = None
    phase: str | None = None
    module_key: str | None = None
    hint: str | None = None
    notes: tuple[str, ...] = ()

    def format_location(self) -> str:
        """
        title: Render the source location without module identity.
        returns:
          type: str
        """
        if self.line is None:
            return ""
        if self.col is None:
            return str(self.line)
        return f"{self.line}:{self.col}"

    def format(self) -> str:
        """
        title: Render the diagnostic for human display.
        returns:
          type: str
        """
        location = self.format_location()
        prefix = f"{location}: " if location else ""
        label = self.severity
        if self.code:
            label = f"{label}[{self.code}]"
        if self.phase and self.phase != "semantic":
            label = f"{label} ({self.phase})"
        lines = [f"{prefix}{label}: {self.message}"]
        for note in self.notes:
            lines.append(f"  note: {note}")
        if self.hint:
            lines.append(f"  hint: {self.hint}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """
        title: Return the formatted diagnostic.
        returns:
          type: str
        """
        return self.format()


def _resolve_source(record: object) -> object | None:
    """
    title: Return the best-effort source location of an IRx diagnostic.
    parameters:
      record:
        type: object
    returns:
      type: object | None
    """
    resolver = getattr(record, "resolved_source", None)
    if callable(resolver):
        resolved: object = resolver()
        return resolved
    source: object = getattr(record, "source", None)
    return source


def _resolve_module_key(record: object) -> str | None:
    """
    title: Return the best-effort module attribution of an IRx diagnostic.
    parameters:
      record:
        type: object
    returns:
      type: str | None
    """
    resolver = getattr(record, "resolved_module_key", None)
    if callable(resolver):
        module_key = resolver()
    else:
        module_key = getattr(record, "module_key", None)
    return module_key if module_key is None else str(module_key)


def diagnostic_from_irx(record: object) -> Diagnostic:
    """
    title: Translate one IRx structured diagnostic into a PyArx Diagnostic.
    description: >-
      Reads the upstream record by attribute so it accepts any
      irx.diagnostics Diagnostic without importing irx. Missing attributes
      fall back to sensible defaults, and a bare message string is accepted
      as a degenerate record.
    parameters:
      record:
        type: object
    returns:
      type: Diagnostic
    """
    if isinstance(record, str):
        return Diagnostic(message=record)

    source = _resolve_source(record)
    notes = tuple(str(note) for note in getattr(record, "notes", ()) or ())
    code = getattr(record, "code", None)
    hint = getattr(record, "hint", None)
    phase = getattr(record, "phase", None)

    return Diagnostic(
        message=str(getattr(record, "message", record)),
        severity=str(getattr(record, "severity", "error")),
        line=getattr(source, "line", None),
        col=getattr(source, "col", None),
        end_line=getattr(source, "end_line", None),
        end_col=getattr(source, "end_col", None),
        code=None if code is None else str(code),
        phase=None if phase is None else str(phase),
        module_key=_resolve_module_key(record),
        hint=None if hint is None else str(hint),
        notes=notes,
    )


def diagnostics_from_irx_error(error: object) -> list[Diagnostic]:
    """
    title: Extract every Diagnostic carried by an IRx error.
    description: >-
      Handles both shapes used by IRx: a single-record error exposing
      `.diagnostic` (IRxDiagnosticError and subclasses) and a bag-bearing error
      exposing `.diagnostics` (SemanticError). Returns an empty list when no
      structured diagnostics are present.
    parameters:
      error:
        type: object
    returns:
      type: list[Diagnostic]
    """
    single = getattr(error, "diagnostic", None)
    if single is not None:
        return [diagnostic_from_irx(single)]

    bag = getattr(error, "diagnostics", None)
    records = getattr(bag, "diagnostics", bag)
    if records is None:
        return []
    return [diagnostic_from_irx(record) for record in records]


__all__ = [
    "Diagnostic",
    "diagnostic_from_irx",
    "diagnostics_from_irx_error",
]
