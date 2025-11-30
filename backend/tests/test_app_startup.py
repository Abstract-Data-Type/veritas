"""
Test for application startup syntax validation.

This test ensures that the main FastAPI application can be imported and
initialized without syntax errors, preventing the IndentationError bug
that was fixed in src/main.py.
"""

from pathlib import Path
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestApplicationStartup:
    """Test suite for application startup validation"""

    def test_main_module_imports_successfully(self):
        """Test that veritas_news.main can be imported without syntax errors"""
        try:
            # This will fail if there are syntax errors in main.py
            import veritas_news.main
            assert hasattr(veritas_news.main, 'app'), "FastAPI app instance should be available"
        except SyntaxError as e:
            pytest.fail(f"Syntax error in main.py: {e}")
        except IndentationError as e:
            pytest.fail(f"Indentation error in main.py: {e}")

    def test_app_instance_creation(self):
        """Test that the FastAPI app instance is properly created"""
        import veritas_news.main

        app = veritas_news.main.app
        assert app is not None, "FastAPI app should not be None"
        assert hasattr(app, 'title'), "FastAPI app should have a title"
        assert app.title == "Veritas News API", f"Expected 'Veritas News API', got '{app.title}'"

    def test_environment_loading_structure(self):
        """Test that environment loading happens before imports (fix validation)"""
        # Read the main.py file and check structure
        main_file = Path(__file__).parent.parent / "src" / "veritas_news" / "main.py"

        with open(main_file) as f:
            content = f.read()

        lines = content.split('\n')

        # Find where load_dotenv is called
        dotenv_line = None
        first_import_line = None

        for i, line in enumerate(lines):
            if 'load_dotenv' in line and dotenv_line is None:
                dotenv_line = i
            elif line.strip().startswith('import ') and 'load_dotenv' not in line and first_import_line is None:
                if not line.strip().startswith('# '):  # Skip comments
                    first_import_line = i

        assert dotenv_line is not None, "load_dotenv should be present in main.py"
        assert first_import_line is not None, "Import statements should be present"

        # Environment loading should happen before other imports (except Path and dotenv)
        # Allow for Path and dotenv imports to come first
        allowed_early_imports = ['from pathlib import Path', 'from dotenv import load_dotenv']

        for i, line in enumerate(lines[:dotenv_line]):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                if not any(allowed in stripped for allowed in allowed_early_imports):
                    pytest.fail(f"Found import before environment loading: {stripped}")

    def test_lifespan_function_exists(self):
        """Test that the lifespan context manager exists and is properly structured"""
        import veritas_news.main

        assert hasattr(veritas_news.main, 'lifespan'), "lifespan function should exist"

        # Test that lifespan is callable (it's an async context manager decorator)
        assert callable(veritas_news.main.lifespan), "lifespan should be callable"

        # Check that it has the @asynccontextmanager decorator behavior
        lifespan_func = veritas_news.main.lifespan
        assert hasattr(lifespan_func, '__call__'), "lifespan should be callable"

    def test_worker_loop_indentation_fix(self):
        """Test that worker_loop function is properly indented (regression test)"""
        main_file = Path(__file__).parent.parent / "src" / "veritas_news" / "main.py"

        with open(main_file) as f:
            content = f.read()

        # Look for the worker_loop function definition
        lines = content.split('\n')
        worker_loop_found = False

        for i, line in enumerate(lines):
            if 'async def worker_loop():' in line:
                worker_loop_found = True
                # Check that this line is properly indented (should be inside a conditional)
                indentation = len(line) - len(line.lstrip())
                assert indentation > 0, "worker_loop should be indented (inside worker_enabled block)"

                # Check that the line before is not a module-level context
                prev_line = lines[i-1].strip() if i > 0 else ""
                assert not prev_line.startswith('if env_path.exists():'), \
                    "worker_loop should not be directly under env_path.exists() block"

                break

        assert worker_loop_found, "worker_loop function should exist in main.py"

    def test_no_syntax_compilation_errors(self):
        """Test that the entire main.py file compiles without syntax errors"""
        main_file = Path(__file__).parent.parent / "src" / "veritas_news" / "main.py"

        with open(main_file) as f:
            content = f.read()

        try:
            # Attempt to compile the code
            compile(content, str(main_file), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Syntax error in main.py at line {e.lineno}: {e.msg}")
        except IndentationError as e:
            pytest.fail(f"Indentation error in main.py at line {e.lineno}: {e.msg}")

    def test_api_routes_registration(self):
        """Test that API routes are properly registered"""
        import veritas_news.main

        app = veritas_news.main.app
        routes = app.routes
        route_paths = [route.path for route in routes if hasattr(route, 'path')]

        # Check for expected route prefixes
        assert any('/bias_ratings' in path for path in route_paths), \
            "bias_ratings routes should be registered"
        assert any('/articles' in path for path in route_paths), \
            "articles routes should be registered"


if __name__ == "__main__":
    # Run tests directly for development
    pytest.main([__file__, "-v"])
