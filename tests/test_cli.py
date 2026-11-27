"""Тесты CLI: запуск точки входа отдельным процессом, как у пользователя."""

import re

from helpers import CLI_EXPECTED, CLI_TREE, listing, make_tree, strip_prefix

PREFIXED = re.compile(r'^(\d{4}) (.+)$')

ROOT_EXPECTED = sorted(
    CLI_EXPECTED[name] for name in CLI_TREE if '/' not in name)


def _names(root):
    return listing(root)


def _stripped(root):
    return sorted(strip_prefix(name) for name in listing(root))


def test_help(run_cli):
    code, text = run_cli('--help')
    assert code == 0
    assert '--testonly' in text
    assert '--output-dir' in text
    assert 'paths' in text


def test_missing_path_fails(run_cli, tmp_path):
    code, text = run_cli(tmp_path / 'nope', '--testonly', '--no-id3')
    assert code == 1
    assert 'не существует' in text


def test_empty_dir_is_not_an_error(run_cli, tmp_path):
    empty = tmp_path / 'empty'
    empty.mkdir()
    code, text = run_cli(empty, '--testonly', '--no-id3')
    assert code == 0
    assert 'не содержит файлов' in text


def test_testonly_does_not_change_files(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', ['Ёлка - Прованс.mp3',
                                          'Привет.mp3'])
    before = _names(root)

    code, text = run_cli(root, '--testonly', '--no-id3')

    assert code == 0
    assert _names(root) == before
    assert 'ТЕСТОВЫЙ РЕЖИМ' in text
    assert 'Elka - Provans.mp3' in text


def test_only_transliterate_renames_in_place(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', CLI_TREE)

    code, _ = run_cli(root, '--only-transliterate', '--no-id3')

    assert code == 0
    assert _names(root) == [
        '### - ##.mp3',
        '01. Kino - Gruppa krovi.mp3',
        'Cafe del Mar - Unicode.mp3',
        'Elka - Provans.mp3',
        'sub/Вложенный - Файл.mp3',
    ]


def test_recursive_transliterates_nested(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', CLI_TREE)

    code, _ = run_cli(root, '--only-transliterate', '--no-id3',
                      '--recursive')

    assert code == 0
    assert 'sub/Vlozhennyi - Fail.mp3' in _names(root)


def test_only_prefixes_adds_prefixes(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', ['Song1.mp3', 'Song2.mp3'])

    code, _ = run_cli(root, '--only-prefixes', '--no-id3')

    assert code == 0
    names = _names(root)
    assert len(names) == 2
    assert all(PREFIXED.match(name) for name in names)
    assert sorted(strip_prefix(name) for name in names) == [
        'Song1.mp3', 'Song2.mp3']


def test_only_prefixes_replaces_existing_prefix(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', ['0001 Song.mp3'])

    code, _ = run_cli(root, '--only-prefixes', '--no-id3')

    assert code == 0
    names = _names(root)
    assert len(names) == 1
    match = PREFIXED.match(names[0])
    assert match is not None
    assert match.group(2) == 'Song.mp3'


def test_output_dir_copies_without_touching_sources(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', CLI_TREE)
    before = _names(root)
    out = tmp_path / 'out'

    code, _ = run_cli(root, '--no-id3', '--output-dir', out)

    assert code == 0
    assert _names(root) == before
    assert _stripped(out) == ROOT_EXPECTED


def test_output_dir_recursive_flattens_nested(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', CLI_TREE)
    out = tmp_path / 'out'

    code, _ = run_cli(root, '--no-id3', '--output-dir', out, '--recursive')

    assert code == 0
    assert _stripped(out) == sorted(CLI_EXPECTED.values())


def test_ge_1000_prefix_range(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', ['Song1.mp3', 'Song2.mp3'])
    out = tmp_path / 'out'

    code, _ = run_cli(root, '--no-id3', '--ge-1000', '--output-dir', out)

    assert code == 0
    numbers = [int(PREFIXED.match(name).group(1)) for name in _names(out)]
    assert len(numbers) == 2
    assert all(1000 <= number <= 9999 for number in numbers)


def test_output_dir_dedupes_same_transliterated_name(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', ['Ёлка.mp3', 'Елка.mp3'])
    out = tmp_path / 'out'

    code, _ = run_cli(root, '--no-id3', '--output-dir', out)

    assert code == 0
    assert _stripped(out) == ['Elka (1).mp3', 'Elka.mp3']


def test_unknown_option_fails(run_cli, tmp_path):
    root = make_tree(tmp_path / 'music', ['Song.mp3'])
    code, text = run_cli(root, '--nope')
    assert code == 2
    assert 'unrecognized arguments' in text


def test_testonly_stops_at_first_error(run_cli, tmp_path):
    """`--testonly` прерывает проверку на первой ошибке (как кнопка в GUI)."""
    missing = tmp_path / 'missing'
    ok = make_tree(tmp_path / 'ok', ['Ёлка - Прованс.mp3'])

    code, text = run_cli(missing, ok, '--testonly', '--no-id3')

    assert code == 1
    assert 'Тестирование прервано на первой ошибке' in text
    # Вторая папка не проверялась и не изменилась.
    assert 'Найдено' not in text
    assert _names(ok) == ['Ёлка - Прованс.mp3']
