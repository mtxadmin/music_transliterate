"""Общие помощники для тестов transliterate (без импорта pytest)."""

import os
import re
from pathlib import Path

PREFIX_RE = re.compile(r'^\d{4} ')
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def strip_prefix(name: str) -> str:
    """Убирает числовой префикс «0000 » из имени файла."""
    return PREFIX_RE.sub('', name)


def strip_ansi(text: str) -> str:
    """Убирает ANSI-раскраску из вывода has_non_ascii()."""
    return ANSI_RE.sub('', text)


def make_tree(root, names):
    """Создаёт дерево файлов; вложенность задаётся через «/» в имени."""
    root = Path(root)
    for name in names:
        path = root.joinpath(*name.split('/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('data:' + name).encode('utf-8'))
    return root


def listing(root):
    """Отсортированный список относительных путей всех файлов."""
    root = Path(root)
    if not root.is_dir():
        return []
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            result.append(full.relative_to(root).as_posix())
    return result


# Небольшой набор для CLI-тестов: кириллица, ё/й, CJK, диакритика, вложенность.
CLI_TREE = [
    '01. Кино - Группа крови.mp3',
    'Ёлка - Прованс.mp3',
    '作曲家 - 歌曲.mp3',
    'Café del Mar - Ünïcode.mp3',
    'sub/Вложенный - Файл.mp3',
]

# Ожидаемые имена после транслитерации (без префиксов и без ID3).
CLI_EXPECTED = {
    '01. Кино - Группа крови.mp3': '01. Kino - Gruppa krovi.mp3',
    'Ёлка - Прованс.mp3': 'Elka - Provans.mp3',
    '作曲家 - 歌曲.mp3': '### - ##.mp3',
    'Café del Mar - Ünïcode.mp3': 'Cafe del Mar - Unicode.mp3',
    'sub/Вложенный - Файл.mp3': 'Vlozhennyi - Fail.mp3',
}

# Золотые значения движка: имя -> (новое имя, определённый язык).
NAMES_CASES = [
    ('01. Кино - Группа крови.mp3', '01. Kino - Gruppa krovi.mp3',
     'russian'),
    ('Ёлка - Прованс.mp3', 'Elka - Provans.mp3', 'russian'),
    ('ёжик в тумане.mp3', 'ezhik v tumane.mp3', 'russian'),
    ('Йошкар-Ола - Песня.mp3', 'Ioshkar-Ola - Pesnya.mp3', 'russian'),
    ('Беларуская песня - Вясна.mp3', 'Belaruskaya pesnya - Vyasna.mp3',
     'russian'),
    ('Українська пісня - Весна.mp3', "Ukrains'ka pisnya - Vesna.mp3",
     'ukrainian'),
    ('Café del Mar - Ünïcode.mp3', 'Cafe del Mar - Unicode.mp3',
     'european'),
    ('Niño - Año.mp3', 'Nino - Ano.mp3', 'european'),
    ('作曲家 - 歌曲.mp3', '### - ##.mp3', 'european'),
    ('★彡 DeCo ★彡 - track.mp3', '# DeCo # - track.mp3', 'european'),
    ('007. Agent - Theme.mp3', '007. Agent - Theme.mp3', 'european'),
    ('1000. Номер - Песня.mp3', '1000. Nomer - Pesnya.mp3', 'russian'),
    ('Сли-я-ние - Дубль.mp3', "Sli-ya-nie - Dubl'.mp3", 'russian'),
    ('Слияние - Дубль.mp3', "Sliyanie - Dubl'.mp3", 'russian'),
    ('Mixed Ёж and Snake.mp3', 'Mixed Ezh and Snake.mp3', 'russian'),
    ('already ascii.mp3', 'already ascii.mp3', 'european'),
    ('Привет.mp3', 'Privet.mp3', 'russian'),
]

# Определение языка по тексту.
LANG_CASES = [
    ('Привет', 'russian'),
    ('Вясна', 'russian'),
    ('Весна', 'russian'),
    ('Straße', 'german'),
    ('Café', 'european'),
    ('Wiosna', None),
    ('Spring', None),
    ('', None),
]

# Очистка недопустимых для файловой системы символов.
SANITIZE_CASES = [
    ('a<b>c:d"e/f\\g|h?i*j', "a_b_c_d'e_f_g_h_i_j"),
    ('нормально.mp3', 'нормально.mp3'),
    ('  пробелы  ', '  пробелы  '),
    ('имя.с.точками.mp3', 'имя.с.точками.mp3'),
]

# Обработка пробелов в _clean_decorative_symbols: пробелы сохраняются,
# повторные схлопываются в один, по краям обрезаются.
CLEAN_CASES = [
    ('a b', 'a b'),
    ('a   b', 'a b'),
    ('  a b  ', 'a b'),
    ('a - b', 'a - b'),
    ('a-b', 'a-b'),
    ('a\u00a0b', 'a b'),   # неразрывный пробел -> обычный
    ('a\tb', 'ab'),        # табуляция (Cc) вырезается, как и раньше
]

# Прямая транслитерация текста.
TRANSLIT_CASES = [
    ('Привет мир', 'Privet mir'),
    ('Ёж', 'Yozh'),
    ('Україна', 'Ukrayina'),
    ('Straße', 'Strasse'),
    ('Café', 'Cafe'),
    ('作曲家', '###'),
    ('abc', 'abc'),
]

# Поиск не-ASCII символов (ANSI-раскраска снимается в тесте).
NON_ASCII_CASES = [
    ('abc', False, 'abc'),
    ('Привет', True, 'Привет'),
    ('aб', True, 'aб'),
    ('', False, ''),
]
