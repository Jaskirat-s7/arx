"""
title: Unit tests for the PyArx exception hierarchy and translators.
"""

from __future__ import annotations

import builtins

import pyarx

from pyarx.diagnostics import Diagnostic
from pyarx.errors import ArxError, CompileError, ParseError, RuntimeError


class _FakeLocation:
    """
    title: Stand-in for an arx lexer SourceLocation.
    """

    def __init__(self, line: int, col: int) -> None:
        """
        title: Initialize the fake location.
        parameters:
          line:
            type: int
          col:
            type: int
        """
        self.line = line
        self.col = col


class _FakeRecord:
    """
    title: Minimal stand-in for an irx structured diagnostic.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        """
        title: Initialize the fake record.
        parameters:
          message:
            type: str
          code:
            type: str | None
        """
        self.message = message
        self.code = code
        self.severity = "error"
        self.phase = "semantic"
        self.source = None


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


def test_hierarchy_and_public_exports() -> None:
    """
    title: Subclasses share ArxError and are re-exported from pyarx.
    """
    for error_type in (ParseError, CompileError, RuntimeError):
        assert issubclass(error_type, ArxError)
    assert pyarx.ArxError is ArxError
    assert pyarx.ParseError is ParseError
    assert pyarx.CompileError is CompileError
    assert pyarx.RuntimeError is RuntimeError
    assert pyarx.Diagnostic is Diagnostic


def test_runtime_error_shadows_builtin() -> None:
    """
    title: The PyArx RuntimeError is distinct from the builtin RuntimeError.
    """
    assert RuntimeError is not builtins.RuntimeError
    assert not issubclass(RuntimeError, builtins.RuntimeError)


def test_base_message_and_format() -> None:
    """
    title: ArxError exposes its message and formats its diagnostics.
    """
    diagnostics = [
        Diagnostic("first", line=1, col=2),
        Diagnostic("second"),
    ]
    error = ArxError("headline", diagnostics=diagnostics)
    assert error.message == "headline"
    assert list(error.diagnostics) == diagnostics
    assert error.format() == "1:2: error: first\nerror: second"


def test_format_falls_back_to_message() -> None:
    """
    title: format returns the message when there are no diagnostics.
    """
    assert ArxError("just a message").format() == "just a message"


def test_parse_error_from_parser_exception_has_no_location() -> None:
    """
    title: from_parser_exception yields a location-free parse diagnostic.
    """
    error = ParseError.from_parser_exception(
        Exception("ParserError: unexpected token")
    )
    assert isinstance(error, ParseError)
    assert error.message == "ParserError: unexpected token"
    (diagnostic,) = error.diagnostics
    assert diagnostic.phase == "parse"
    assert diagnostic.line is None
    assert diagnostic.col is None


def test_parse_error_from_lexer_error_copies_location() -> None:
    """
    title: from_lexer_error copies the lexer location onto the diagnostic.
    """

    class _FakeLexerError(Exception):
        """
        title: Stand-in for an arx LexerError.
        """

        def __init__(self) -> None:
            """
            title: Initialize the fake lexer error.
            """
            super().__init__("bad char at line 5, col 9")
            self.location = _FakeLocation(5, 9)

    error = ParseError.from_lexer_error(_FakeLexerError())
    (diagnostic,) = error.diagnostics
    assert diagnostic.phase == "lex"
    assert diagnostic.line == 5
    assert diagnostic.col == 9


def test_compile_error_from_irx_error_preserves_diagnostics() -> None:
    """
    title: from_irx_error preserves every diagnostic and picks a headline.
    """
    error = CompileError.from_irx_error(
        _FakeSemanticError(
            [_FakeRecord("unresolved name", code="S001"), _FakeRecord("x")]
        )
    )
    assert isinstance(error, CompileError)
    assert error.message == "unresolved name"
    assert [diagnostic.message for diagnostic in error.diagnostics] == [
        "unresolved name",
        "x",
    ]


def test_compile_error_from_irx_error_without_diagnostics() -> None:
    """
    title: A diagnostic-free irx error falls back to its string form.
    """
    error = CompileError.from_irx_error(Exception("internal failure"))
    assert error.message == "internal failure"
    assert error.diagnostics == []
