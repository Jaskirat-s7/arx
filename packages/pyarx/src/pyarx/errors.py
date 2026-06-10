"""
title: Public exception hierarchy for the PyArx API.
summary: >-
  Define the single error hierarchy PyArx raises to callers: ArxError as the
  base, with ParseError, CompileError, and RuntimeError for the lex/parse,
  analysis/lowering, and execution stages of the pipeline. Each error carries
  a list of structured Diagnostic records so callers can inspect failures
  programmatically instead of scraping message text. Translation helpers
  convert upstream arx and irx exceptions into these types; like
  diagnostics.py they are duck-typed and never import arx or irx at load time.
"""

from __future__ import annotations

from collections.abc import Sequence

from pyarx.diagnostics import Diagnostic, diagnostics_from_irx_error


def _primary_message(
    diagnostics: Sequence[Diagnostic],
    fallback: str,
) -> str:
    """
    title: Pick the headline message for an error.
    parameters:
      diagnostics:
        type: Sequence[Diagnostic]
      fallback:
        type: str
    returns:
      type: str
    """
    if diagnostics:
        return diagnostics[0].message
    return fallback


class ArxError(Exception):
    """
    title: Base class for every error raised by the PyArx API.
    attributes:
      diagnostics:
        type: list[Diagnostic]
        description: Structured diagnostics describing the failure.
    """

    diagnostics: list[Diagnostic]

    def __init__(
        self,
        message: str,
        *,
        diagnostics: Sequence[Diagnostic] | None = None,
    ) -> None:
        """
        title: Initialize an ArxError.
        parameters:
          message:
            type: str
          diagnostics:
            type: Sequence[Diagnostic] | None
        """
        self.diagnostics = list(diagnostics or ())
        super().__init__(message)

    @property
    def message(self) -> str:
        """
        title: Return the headline error message.
        returns:
          type: str
        """
        return str(self.args[0]) if self.args else ""

    def format(self) -> str:
        """
        title: Render the error and its diagnostics for display.
        returns:
          type: str
        """
        if self.diagnostics:
            return "\n".join(
                diagnostic.format() for diagnostic in self.diagnostics
            )
        return self.message


class ParseError(ArxError):
    """
    title: Raised when lexing or parsing Arx source fails.
    """

    @classmethod
    def from_parser_exception(cls, error: Exception) -> ParseError:
        """
        title: Build a ParseError from an arx ParserException.
        description: >-
          ParserException discards token location in v1, so the resulting
          diagnostic has no line or column.
        parameters:
          error:
            type: Exception
        returns:
          type: ParseError
        """
        message = str(error)
        diagnostic = Diagnostic(message=message, phase="parse")
        return cls(message, diagnostics=[diagnostic])

    @classmethod
    def from_lexer_error(cls, error: Exception) -> ParseError:
        """
        title: Build a ParseError from an arx LexerError.
        description: >-
          LexerError carries a source location; its line and column are copied
          onto the diagnostic when present.
        parameters:
          error:
            type: Exception
        returns:
          type: ParseError
        """
        message = str(error)
        location = getattr(error, "location", None)
        diagnostic = Diagnostic(
            message=message,
            phase="lex",
            line=getattr(location, "line", None),
            col=getattr(location, "col", None),
        )
        return cls(message, diagnostics=[diagnostic])


class CompileError(ArxError):
    """
    title: Raised when semantic analysis, lowering, or codegen fails.
    """

    @classmethod
    def from_irx_error(cls, error: Exception) -> CompileError:
        """
        title: Build a CompileError from an irx diagnostic-bearing error.
        description: >-
          Accepts both the single-record IRxDiagnosticError family and the
          bag-bearing SemanticError, preserving each structured diagnostic.
        parameters:
          error:
            type: Exception
        returns:
          type: CompileError
        """
        diagnostics = diagnostics_from_irx_error(error)
        message = _primary_message(diagnostics, str(error))
        return cls(message, diagnostics=diagnostics)


class RuntimeError(ArxError):
    """
    title: Raised when running a compiled Arx program fails to execute.
    description: >-
      Reserved for failures that prevent execution from completing, such as a
      missing binary or a timeout. A program that runs to completion with a
      non-zero exit code is reported as data, not raised.
    """


__all__ = [
    "ArxError",
    "CompileError",
    "ParseError",
    "RuntimeError",
]
