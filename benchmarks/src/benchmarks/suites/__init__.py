"""benchmark-suite package."""

from benchmarks.suites.loader import SuiteSpec, load_suites, register

__all__ = ["SuiteSpec", "load_suites", "register"]