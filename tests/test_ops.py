"""Тесты файловых операций (ops): префиксы, копирование, пакет папок."""

import re

import pytest

from helpers import CLI_TREE, listing, make_tree, strip_prefix


def test_get_config_path_points_to_public_dir(modules, public_dir):
    """Конфиг ищется рядом со скриптами, а не в текущем каталоге."""
    path = modules.ops.get_config_path()
    assert path.parent == public_dir
    assert path.name == 'music_transliterate.config'


def test_add_number_prefixes(modules, tmp_path):
    """Каждому файлу достаётся уникальный префикс «0000 »."""
    root = make_tree(tmp_path / 'music', ['Song1.mp3', 'Song2.mp3'])

    modules.ops.add_number_prefixes(str(root))

    names = listing(root)
    assert len(names) == 2
    assert all(name[:4].isdigit() and name[4] == ' ' for name in names)
    assert sorted(strip_prefix(name) for name in names) == [
        'Song1.mp3', 'Song2.mp3']


def test_add_number_prefixes_replaces_existing(modules, tmp_path):
    """Старый префикс не удваивается, а заменяется новым."""
    root = make_tree(tmp_path / 'music', ['0001 Song.mp3'])

    modules.ops.add_number_prefixes(str(root))

    names = listing(root)
    assert len(names) == 1
    assert re.fullmatch(r'\d{4} Song\.mp3', names[0]), names[0]


def test_add_number_prefixes_ge_1000(modules, tmp_path):
    root = make_tree(tmp_path / 'music', ['Song.mp3'])

    modules.ops.add_number_prefixes(str(root), flag_ge_1000=True)

    number = int(listing(root)[0][:4])
    assert 1000 <= number <= 9999


def test_add_number_prefixes_reports_missing_dir(modules, tmp_path):
    with pytest.raises(ValueError):
        modules.ops.add_number_prefixes(str(tmp_path / 'nope'))


def test_run_operation_testonly_does_not_touch_files(modules, tmp_path):
    root = make_tree(tmp_path / 'music', CLI_TREE)
    before = listing(root)

    modules.ops.run_operation(
        str(root), add_prefixes=False, transliterate_names=True,
        transliterate_id3=False, testonly=True, recursive=True)

    assert listing(root) == before


def test_run_operation_renames_in_place(modules, tmp_path):
    root = make_tree(tmp_path / 'music', ['Ёлка - Прованс.mp3',
                                          'Привет.mp3'])

    modules.ops.run_operation(
        str(root), add_prefixes=False, transliterate_names=True,
        transliterate_id3=False)

    assert listing(root) == ['Elka - Provans.mp3', 'Privet.mp3']


def test_run_operation_missing_path_raises(modules, tmp_path):
    with pytest.raises(RuntimeError):
        modules.ops.run_operation(
            str(tmp_path / 'nope'), add_prefixes=False,
            transliterate_names=True, transliterate_id3=False)


def test_output_dir_keeps_sources_and_dedupes_names(modules, tmp_path):
    """Два разных имени, дающих одно и то же, не затирают друг друга."""
    root = make_tree(tmp_path / 'music', ['Ёлка.mp3', 'Елка.mp3'])
    out = tmp_path / 'out'

    modules.ops.run_operation(
        str(root), add_prefixes=False, transliterate_names=True,
        transliterate_id3=False, output_dir=str(out))

    assert listing(root) == ['Ёлка.mp3', 'Елка.mp3']
    assert sorted(strip_prefix(name) for name in listing(out)) == [
        'Elka (1).mp3', 'Elka.mp3']


def test_run_batch_collects_success_and_failures(modules, tmp_path):
    ok = make_tree(tmp_path / 'ok', ['Ёлка.mp3'])
    missing = tmp_path / 'missing'

    result = modules.ops.run_batch(
        [{'path': str(ok), 'ge_1000': False, 'recursive': False},
         {'path': str(missing), 'ge_1000': False, 'recursive': False}],
        output_dir=None, testonly=True,
        add_prefixes=False, transliterate_names=True,
        transliterate_id3=False)

    assert result['success'] == [str(ok)]
    assert [path for path, _ in result['failed']] == [str(missing)]


def test_run_batch_testonly_stops_on_first_error(modules, tmp_path, capsys):
    """В тестовом режиме проверка прерывается на первой же ошибке."""
    missing = tmp_path / 'missing'
    ok = make_tree(tmp_path / 'ok', ['Ёлка.mp3'])

    result = modules.ops.run_batch(
        [{'path': str(missing), 'ge_1000': False, 'recursive': False},
         {'path': str(ok), 'ge_1000': False, 'recursive': False}],
        output_dir=None, testonly=True,
        add_prefixes=False, transliterate_names=True,
        transliterate_id3=False)

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert result['success'] == []
    assert [path for path, _ in result['failed']] == [str(missing)]
    assert 'Тестирование прервано на первой ошибке' in output
    assert 'Не проверено папок: 1' in output
    # Вторая папка действительно не проверялась.
    assert 'Найдено' not in captured.out


def test_run_batch_real_mode_continues_after_error(modules, tmp_path, capsys):
    """В боевом режиме ошибка одной папки не останавливает остальные."""
    missing = tmp_path / 'missing'
    ok = make_tree(tmp_path / 'ok', ['Ёлка.mp3'])

    result = modules.ops.run_batch(
        [{'path': str(missing), 'ge_1000': False, 'recursive': False},
         {'path': str(ok), 'ge_1000': False, 'recursive': False}],
        output_dir=None, testonly=False,
        add_prefixes=False, transliterate_names=True,
        transliterate_id3=False)

    captured = capsys.readouterr()
    assert result['success'] == [str(ok)]
    assert [path for path, _ in result['failed']] == [str(missing)]
    assert 'Тестирование прервано' not in captured.out + captured.err
    # Вторая папка действительно обработана.
    assert listing(ok) == ['Elka.mp3']
