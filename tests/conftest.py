"""Фикстуры для тестов transliterate-скрипта.

Все пути считаются от файлов, а не от текущего каталога.
"""

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = TESTS_DIR.parent
ENTRY = PUBLIC_DIR / 'music_transliterate.py'

# Чтобы `from helpers import ...` работал при любом способе запуска pytest.
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(PUBLIC_DIR) not in sys.path:
    sys.path.insert(0, str(PUBLIC_DIR))


def pytest_configure(config):
    """Маркер gui объявлен и здесь: тесты работают и вне корня репозитория."""
    config.addinivalue_line('markers', 'gui: тест открывает окно Tk')


@pytest.fixture(scope='session')
def public_dir():
    return PUBLIC_DIR


@pytest.fixture(scope='session')
def modules():
    """Движок, таблицы и файловые операции, импортированные из:"""
    import music_transliterate_core as core
    import music_transliterate_ops as ops
    import music_transliterate_tables as tables
    return types.SimpleNamespace(core=core, ops=ops, tables=tables)


@pytest.fixture
def transliterator(modules):
    return modules.core.FileTransliterator()


@pytest.fixture
def run_cli(tmp_path):
    """Запускает точку входа отдельным процессом, как это делает пользователь.

    Возвращает (код возврата, объединённый stdout+stderr).
    """
    def run(*args, cwd=None, timeout=180):
        env = dict(os.environ)
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        proc = subprocess.run(
            [sys.executable, str(ENTRY)] + [str(a) for a in args],
            cwd=str(cwd or tmp_path),
            capture_output=True,
            env=env,
            timeout=timeout,
        )
        text = (proc.stdout + proc.stderr).decode('utf-8', 'replace')
        return proc.returncode, text

    return run


@pytest.fixture
def entry_module():
    """Модуль точки входа (GUI/CLI), импортированный по пути."""
    spec = importlib.util.spec_from_file_location('mt_entry_under_test',
                                                  ENTRY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
