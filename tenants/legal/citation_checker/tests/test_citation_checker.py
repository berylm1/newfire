"""Basic tests for citation_checker module structure and imports."""
import pytest


class TestCitationCheckerImports:
    """Verify the citation_checker modules can be imported."""

    def test_graph_module_exists(self):
        """Verify graph.py can be parsed for basic structure."""
        import pathlib
        graph_file = pathlib.Path(__file__).parent.parent / "graph.py"
        assert graph_file.exists(), "graph.py should exist in citation_checker"
        content = graph_file.read_text()
        assert "from langchain" in content or "from langgraph" in content, \
            "graph.py should import from langchain/langgraph"

    def test_courtlistener_module_exists(self):
        """Verify courtlistener.py can be parsed for basic structure."""
        import pathlib
        cl_file = pathlib.Path(__file__).parent.parent / "courtlistener.py"
        assert cl_file.exists(), "courtlistener.py should exist in citation_checker"
        content = cl_file.read_text()
        assert "courtlistener" in content.lower(), \
            "courtlistener.py should reference courtlistener"

    def test_run_module_exists(self):
        """Verify run.py can be parsed for basic structure."""
        import pathlib
        run_file = pathlib.Path(__file__).parent.parent / "run.py"
        assert run_file.exists(), "run.py should exist in citation_checker"
        content = run_file.read_text()
        assert "def main" in content or "if __name__" in content, \
            "run.py should have a main entry point"


class TestCitationCheckerConfig:
    """Verify citation_checker uses shared LLM config."""

    def test_graph_uses_llm_config(self):
        """graph.py should import from shared.llm_config."""
        import pathlib
        graph_file = pathlib.Path(__file__).parent.parent / "graph.py"
        content = graph_file.read_text()
        assert "from shared.llm_config" in content, \
            "graph.py should use shared llm_config for LLM configuration"
