"""
title: Unit tests for the PyArx Diagnostic record and IRx translation helpers.
"""

from __future__ import annotations

from pyarx.diagnostics import (
    Diagnostic,
    diagnostic_from_irx,
    diagnostics_from_irx_error,
)


class _FakeSource:
    """
    title: Stand-in for an irx SourceLocation.
    """

    def __init__(
        self,
        line: int | None,
        col: int | None,
        end_line: int | None = None,
        end_col: int | None = None,
    ) -> None:
        """
        title: Initialize the fake source location.
        parameters:
          line:
            type: int | None
          col:
            type: int | None
          end_line:
            type: int | None
          end_col:
            type: int | None
        """
        self.line = line
        self.col = col
        self.end_line = end_line
        self.end_col = end_col


class _FakeRecord:
    """
    title: Stand-in for an irx structured Diagnostic.
    """

    def __init__(
        self,
        message: str,
        *,
        source: _FakeSource | None = None,
        severity: str = "error",
        code: str | None = None,
        phase: str = "semantic",
        hint: str | None = None,
        notes: tuple[str, ...] = (),
        module_key: str | None = None,
    ) -> None:
        """
        title: Initialize the fake record.
        parameters:
          message:
            type: str
          source:
            type: _FakeSource | None
          severity:
            type: str
          code:
            type: str | None
          phase:
            type: str
          hint:
            type: str | None
          notes:
            type: tuple[str, ...]
          module_key:
            type: str | None
        """
        self.message = message
        self.source = source
        self.severity = severity
        self.code = code
        self.phase = phase
        self.hint = hint
        self.notes = notes
        self.module_key = module_key

    def resolved_source(self) -> _FakeSource | None:
        """
        title: Return the resolved source location.
        returns:
          type: _FakeSource | None
        """
        return self.source

    def resolved_module_key(self) -> str | None:
        """
        title: Return the resolved module attribution.
        returns:
          type: str | None
        """
        return self.module_key


def test_format_location_variants() -> None:
    """
    title: format_location renders line-only, line:col, and empty cases.
    """
    assert Diagnostic("m").format_location() == ""
    assert Diagnostic("m", line=4).format_location() == "4"
    assert Diagnostic("m", line=4, col=7).format_location() == "4:7"


def test_format_includes_code_phase_notes_hint() -> None:
    """
    title: format renders location, code, phase, notes, and hint.
    """
    diagnostic = Diagnostic(
        message="bad name",
        line=3,
        col=5,
        code="S001",
        phase="lex",
        hint="declare it first",
        notes=("seen here", "and here"),
    )
    rendered = diagnostic.format()
    assert rendered.splitlines() == [
        "3:5: error[S001] (lex): bad name",
        "  note: seen here",
        "  note: and here",
        "  hint: declare it first",
    ]
    assert str(diagnostic) == rendered


def test_format_omits_semantic_phase_label() -> None:
    """
    title: The default "semantic" phase is not shown in the label.
    """
    assert Diagnostic("m", phase="semantic").format() == "error: m"


def test_diagnostic_from_irx_copies_fields() -> None:
    """
    title: diagnostic_from_irx maps every field from a structured record.
    """
    record = _FakeRecord(
        "unresolved name x",
        source=_FakeSource(2, 6, end_line=2, end_col=7),
        code="S001",
        phase="semantic",
        hint="define x",
        notes=("note one",),
        module_key="main",
    )
    diagnostic = diagnostic_from_irx(record)
    assert diagnostic == Diagnostic(
        message="unresolved name x",
        severity="error",
        line=2,
        col=6,
        end_line=2,
        end_col=7,
        code="S001",
        phase="semantic",
        module_key="main",
        hint="define x",
        notes=("note one",),
    )


def test_diagnostic_from_irx_without_source() -> None:
    """
    title: A record with no source yields a location-free diagnostic.
    """
    diagnostic = diagnostic_from_irx(_FakeRecord("oops"))
    assert diagnostic.line is None
    assert diagnostic.col is None
    assert diagnostic.format_location() == ""


def test_diagnostic_from_irx_accepts_bare_string() -> None:
    """
    title: A bare string is accepted as a degenerate record.
    """
    assert diagnostic_from_irx("plain message") == Diagnostic(
        message="plain message"
    )


class _FakeBag:
    """
    title: Stand-in for an irx DiagnosticBag.
    """

    def __init__(self, diagnostics: list[_FakeRecord]) -> None:
        """
        title: Initialize the fake bag.
        parameters:
          diagnostics:
            type: list[_FakeRecord]
        """
        self.diagnostics = diagnostics


class _FakeSemanticError(Exception):
    """
    title: Stand-in for an irx SemanticError carrying a bag.
    """

    def __init__(self, diagnostics: list[_FakeRecord]) -> None:
        """
        title: Initialize the fake semantic error.
        parameters:
          diagnostics:
            type: list[_FakeRecord]
        """
        super().__init__("semantic failure")
        self.diagnostics = _FakeBag(diagnostics)


class _FakeIRxDiagnosticError(Exception):
    """
    title: Stand-in for an irx single-record IRxDiagnosticError.
    """

    def __init__(self, diagnostic: _FakeRecord) -> None:
        """
        title: Initialize the fake single-record error.
        parameters:
          diagnostic:
            type: _FakeRecord
        """
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def test_diagnostics_from_irx_error_single_record() -> None:
    """
    title: A single-record error yields exactly one diagnostic.
    """
    error = _FakeIRxDiagnosticError(_FakeRecord("link failed", code="K001"))
    diagnostics = diagnostics_from_irx_error(error)
    assert [diagnostic.message for diagnostic in diagnostics] == [
        "link failed"
    ]
    assert diagnostics[0].code == "K001"


def test_diagnostics_from_irx_error_bag() -> None:
    """
    title: A bag-bearing error yields one diagnostic per record.
    """
    error = _FakeSemanticError([_FakeRecord("first"), _FakeRecord("second")])
    diagnostics = diagnostics_from_irx_error(error)
    assert [diagnostic.message for diagnostic in diagnostics] == [
        "first",
        "second",
    ]


def test_diagnostics_from_irx_error_empty() -> None:
    """
    title: An error with no structured diagnostics yields an empty list.
    """
    assert diagnostics_from_irx_error(Exception("boom")) == []
