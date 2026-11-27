"""Структура публикуемой папки: файлы, кодировки, слои зависимостей."""

import ast
import re
import subprocess
import sys

import pytest

ENTRY = 'music_transliterate.py'
CORE = 'music_transliterate_core.py'
OPS = 'music_transliterate_ops.py'
TABLES = 'music_transliterate_tables.py'

FILES = [ENTRY, CORE, OPS, TABLES]
ENGINE_FILES = [CORE, OPS, TABLES]

LOCAL_IMPORT_RE = re.compile(
    r'^\s*(?:from|import)\s+(music_transliterate\w*)', re.MULTILINE)

GUI_IMPORTS = ('import tkinter', 'from tkinter', 'import yaml',
               'from yaml')


def read(public_dir, name):
    return (public_dir / name).read_text(encoding='utf-8-sig')


def local_imports(public_dir, name):
    return set(LOCAL_IMPORT_RE.findall(read(public_dir, name)))


@pytest.mark.parametrize('name', FILES)
def test_file_exists(public_dir, name):
    path = public_dir / name
    assert path.is_file()
    assert path.stat().st_size > 0


@pytest.mark.parametrize('name', FILES)
def test_utf8_bom_and_crlf(public_dir, name):
    """Как в исходном файле: UTF-8 BOM и переводы строк только CRLF."""
    raw = (public_dir / name).read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')
    assert raw.count(b'\n') == raw.count(b'\r\n')


@pytest.mark.parametrize('name', ENGINE_FILES)
def test_engine_has_no_gui_dependencies(public_dir, name):
    for line in read(public_dir, name).splitlines():
        assert not line.startswith(GUI_IMPORTS), f'{name}: {line}'


@pytest.mark.parametrize('name', FILES)
def test_compiles(public_dir, name):
    path = public_dir / name
    compile(read(public_dir, name), str(path), 'exec')


def test_dependency_layers(public_dir):
    """tables <- core <- ops <- entry, без обратных зависимостей."""
    assert local_imports(public_dir, TABLES) == set()
    assert local_imports(public_dir, CORE) == {'music_transliterate_tables'}
    assert local_imports(public_dir, OPS) == {'music_transliterate_core'}
    assert local_imports(public_dir, ENTRY) == {
        'music_transliterate_core', 'music_transliterate_ops'}


def _top_level_defs(public_dir, name):
    path = public_dir / name
    tree = ast.parse(read(public_dir, name), str(path))
    return [node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef))]


def test_no_duplicate_top_level_definitions(public_dir):
    """Разделение файлов не должно оставлять копий функций или классов."""
    seen = {}
    for name in FILES:
        for def_name in _top_level_defs(public_dir, name):
            assert def_name not in seen, (
                f'{def_name}: определён и в {seen[def_name]}, и в {name}')
            seen[def_name] = name


def test_expected_definitions(public_dir):
    assert set(_top_level_defs(public_dir, TABLES)) == {
        'TransliterationTablesMixin'}
    assert set(_top_level_defs(public_dir, CORE)) == {
        'safe_stderr_write', 'safe_stdout_write', 'FileTransliterator'}
    assert set(_top_level_defs(public_dir, OPS)) == {
        'add_number_prefixes', '_preview_prefixes', '_copy_files_to_output',
        'run_operation_output', 'run_operation', 'run_batch',
        'get_config_path'}
    assert set(_top_level_defs(public_dir, ENTRY)) == {
        'QueueWriter', 'ScrollableFrame', 'FolderRow', 'App',
        '_run_cli', 'main'}


def test_modules_import_from_public_dir(public_dir):
    code = (
        'import music_transliterate_core as c\n'
        'import music_transliterate_ops as o\n'
        'import music_transliterate_tables as t\n'
        'assert hasattr(c, "FileTransliterator")\n'
        'assert hasattr(o, "run_batch")\n'
        'assert hasattr(o, "run_operation")\n'
        'assert hasattr(o, "get_config_path")\n'
        'assert hasattr(t, "TransliterationTablesMixin")\n'
        'print("ok")\n'
    )
    proc = subprocess.run([sys.executable, '-c', code],
                          cwd=str(public_dir), capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode('utf-8', 'replace')


def test_entry_api(entry_module):
    assert callable(entry_module.main)
    assert callable(entry_module._run_cli)
    # Движок живёт в core, а не в точке входа.
    assert not hasattr(entry_module, 'FileTransliterator')
