from pathlib import Path

from utils.excel import discover_workbook, parse_project_workbook
from utils.schemas import ParsedProject


class ParserAgent:
    """Discovers workbook structure and parses project data without hardcoded sheet names."""

    def inspect(self, path: str | Path) -> dict:
        return discover_workbook(path)

    def run(self, path: str | Path) -> ParsedProject:
        return parse_project_workbook(path)
