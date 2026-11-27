"""Тесты движка: таблицы транслитерации, имена файлов, ID3-независимая логика."""

import pytest

from helpers import (CLEAN_CASES, LANG_CASES, NAMES_CASES, NON_ASCII_CASES,
                     SANITIZE_CASES, TRANSLIT_CASES, strip_ansi)

LANGUAGES = ['bulgarian', 'european', 'german', 'polish', 'russian',
             'ukrainian']

TABLE_SIZES = {
    'russian': 295,
    'ukrainian': 87,
    'polish': 39,
    'bulgarian': 81,
    'german': 28,
    'european': 897,
}

# Контрольные символы: если таблицу случайно «почистят», тест это заметит.
# Последние четыре символа в 'russian' (ǝ Ǝ ə Ə) — не «русские буквы»,
# а декоративный слой _add_decorative_latin, который добавляется в русскую
# и европейскую таблицы (см. комментарий в music_transliterate_tables.py).
TABLE_SPOT = {
    'russian': {'ё': 'yo', 'й': 'y', 'ъ': "'", 'ь': "'", 'ы': 'y',
                'ǝ': 'e', 'Ǝ': 'E', 'ə': 'e', 'Ə': 'E'},
    'ukrainian': {'ї': 'yi', 'і': 'i', 'є': 'ye', 'ґ': 'g'},
    'german': {'ß': 'ss', 'ä': 'ae', 'ö': 'oe', 'ü': 'ue'},
    'european': {'é': 'e', 'ñ': 'n', 'ç': 'c', 'ø': 'o', 'œ': 'oe',
                 'å': 'a', 'æ': 'ae'},
    'polish': {'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
               'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'},
}

EXTRA_NAMES = [
    ('track.mp3', 'track.mp3', 'european'),
    ('Track 01.mp3', 'Track 01.mp3', 'european'),
    ('file.MP3', 'file.MP3', 'european'),
    ('трек (1).mp3', 'trek (1).mp3', 'russian'),
    ('Ünïcode.mp3', 'Unicode.mp3', 'european'),
    ('a  b.mp3', 'a b.mp3', 'european'),
]


def test_languages_present(modules):
    tables = modules.core.FileTransliterator().transliteration_tables
    assert sorted(tables) == LANGUAGES


@pytest.mark.parametrize('language,size', sorted(TABLE_SIZES.items()))
def test_table_sizes(modules, language, size):
    tables = modules.core.FileTransliterator().transliteration_tables
    assert len(tables[language]) == size


@pytest.mark.parametrize('language,pairs', sorted(TABLE_SPOT.items()))
def test_table_spot_checks(modules, language, pairs):
    table = modules.core.FileTransliterator().transliteration_tables[language]
    got = {char: table.get(char) for char in pairs}
    assert got == pairs


def test_tables_are_built_by_mixin(modules):
    core, tables = modules.core, modules.tables
    assert issubclass(core.FileTransliterator,
                      tables.TransliterationTablesMixin)
    mro = [cls.__name__ for cls in core.FileTransliterator.__mro__]
    assert mro == ['FileTransliterator', 'TransliterationTablesMixin',
                   'object']
    for name in ('_add_extra_cyrillic', '_add_decorative_latin',
                 '_create_transliteration_tables'):
        method = getattr(core.FileTransliterator, name)
        assert method.__qualname__ == f'TransliterationTablesMixin.{name}'


@pytest.mark.parametrize('filename,expected,language', NAMES_CASES)
def test_process_filename(transliterator, filename, expected, language):
    assert transliterator.process_filename(filename) == (expected, language)


@pytest.mark.parametrize('filename,expected,language', EXTRA_NAMES)
def test_process_filename_edge_cases(transliterator, filename, expected,
                                     language):
    assert transliterator.process_filename(filename) == (expected, language)


@pytest.mark.parametrize('text,expected', LANG_CASES)
def test_detect_language(transliterator, text, expected):
    assert transliterator.detect_language(text) == expected


def test_bulgarian_hard_sign_is_a_vowel(transliterator):
    """Болгарский: "ъ" — гласная, в русском он стоит только перед е/ё/ю/я."""
    for text in ('Път към дома', 'Мъжът и жената', 'Сънят', 'Сълзи',
                 'Дъжд вали', 'Пътуване'):
        assert transliterator.detect_language(text) == 'bulgarian'
    for text in ('Съезд', 'Объявление', 'Подъезд', 'Разъяснение',
                 'Адъютант', 'Инъекция', 'Съёмка'):
        assert transliterator.detect_language(text) == 'russian'


def test_bulgarian_lexicon_without_hard_sign(transliterator):
    """Названия без "ъ", где различие только в щ/х/ь, ловит словарь."""
    for text in ('Щастие', 'Още малко', 'Нощта е тиха', 'Хубава си',
                 'Актьор', 'Шофьор', 'Режисьор'):
        assert transliterator.detect_language(text) == 'bulgarian'


def test_russian_words_are_not_bulgarian(transliterator):
    """Русские слова с щ/х/ъ не должны попадать в болгарский."""
    for text in ('Щука', 'Хлеб и соль', 'Мощь', 'Защита', 'Холодно',
                 'Хора', 'Храм', 'Хотел', 'Пещера', 'Вещи', 'После',
                 'Много', 'Само', 'Вече'):
        assert transliterator.detect_language(text) == 'russian'


def test_word_final_hard_sign_is_ambiguous(transliterator):
    """В конце слова "ъ" — русская стилизация ("Барнаулъ"), а не болгарский."""
    for text in ('Барнаулъ', 'Пиздецъ', 'Бульваръ', 'Орехъ', 'Разгромъ',
                 'Безъимянная', 'Vъlica'):
        assert transliterator.detect_language(text) == 'russian'


def test_ukrainian_shche_is_not_bulgarian(transliterator):
    """Украинское "ще" пишется как болгарское, но і/ї/є выдают украинский."""
    for text in ('Скільки Ще', 'Так Ніхто Ще Не Кохав',
                 'Я Тебе Ще Більше Кохаю'):
        assert transliterator.detect_language(text) == 'ukrainian'


def test_bulgarian_transliteration(transliterator):
    """Болгарская таблица: ъ -> a, щ -> sht, х -> h, ь -> y."""
    assert transliterator.process_filename('Път към дома.mp3') == (
        'Pat kam doma.mp3', 'bulgarian')
    assert transliterator.process_filename('Мъжът и жената.mp3') == (
        'Mazhat i zhenata.mp3', 'bulgarian')
    assert transliterator.process_filename('Щастие.mp3') == (
        'Shtastie.mp3', 'bulgarian')
    assert transliterator.process_filename('Хубава си.mp3') == (
        'Hubava si.mp3', 'bulgarian')
    assert transliterator.process_filename('Актьор.mp3') == (
        'Aktyor.mp3', 'bulgarian')


def test_decoration_falls_back_to_european_table(transliterator):
    """Декорация в имени, для которого выбрана таблица без декоративного слоя.

    Регрессия: "Українська ǝ.mp3" падала с ошибкой «остались не-ASCII»,
    потому что декоративный слой есть только в русской и европейской
    таблицах. Недостающие символы берутся из европейской таблицы, а не
    заменяют язык целиком ("Pat e", а не "P't e").
    """
    assert transliterator.process_filename('Українська ǝ.mp3') == (
        "Ukrains'ka e.mp3", 'ukrainian')
    assert transliterator.process_filename('Път ǝ.mp3') == (
        'Pat e.mp3', 'bulgarian')
    assert transliterator.process_filename('Хубава ᴢвезда.mp3') == (
        'Hubava Zvezda.mp3', 'bulgarian')


@pytest.mark.parametrize('text,expected', SANITIZE_CASES)
def test_sanitize_filename(transliterator, text, expected):
    assert transliterator.sanitize_filename(text) == expected


@pytest.mark.parametrize('text,expected', CLEAN_CASES)
def test_clean_decorative_symbols_keeps_spaces(transliterator, text, expected):
    assert transliterator._clean_decorative_symbols(text) == expected


def test_process_filename_keeps_spaces(transliterator):
    """Пробелы в имени сохраняются.

    Регрессия: набор разрешённых категорий содержал 'Zs' вместо префикса 'Z',
    поэтому все пробелы вырезались ('Elka-Provans' вместо 'Elka - Provans').
    """
    assert transliterator.process_filename('Кино - Группа крови.mp3') == (
        'Kino - Gruppa krovi.mp3', 'russian')


@pytest.mark.parametrize('text,expected', TRANSLIT_CASES)
def test_transliterate_text(transliterator, text, expected):
    assert transliterator.transliterate_text(text) == expected


def test_latin_x_is_not_uppercased(transliterator):
    """Декоративный слой не трогает обычную латинскую «x».

    Регрессия: в _add_decorative_latin было 'x': 'X', из-за чего
    'Maxx.mp3' превращался в 'MaXX.mp3'.
    """
    for language in ('russian', 'european'):
        assert transliterator.transliterate_text('Maxx', language) == 'Maxx'
    assert transliterator.process_filename('Maxx.mp3') == (
        'Maxx.mp3', 'european')
    # Small Caps при этом продолжают работать.
    assert transliterator.transliterate_text('ᴍᴀx', 'russian') == 'MAx'


@pytest.mark.parametrize('text,flag,fragment', NON_ASCII_CASES)
def test_has_non_ascii(transliterator, text, flag, fragment):
    found, marked = transliterator.has_non_ascii(text)
    assert found is flag
    assert strip_ansi(marked) == fragment


def test_ascii_name_is_unchanged(transliterator):
    """Чисто ASCII-имя движок не трогает."""
    assert transliterator.process_filename('track.mp3') == (
        'track.mp3', 'european')


def test_file_state_can_be_reset(transliterator):
    """Сброс состояния файла очищает все поля."""
    transliterator.file_state['original'] = 'старое.mp3'
    transliterator.file_state['language'] = 'russian'
    transliterator._reset_file_state()
    assert set(transliterator.file_state.values()) == {None}
