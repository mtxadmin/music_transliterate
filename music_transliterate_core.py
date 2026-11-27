# https://github.com/mtxadmin/music_transliterate/
# Many thanks to Deepseek AI, who greatly helped with writing and debugging of this script


# модуль transliterate - херня, детектит всё как ru. Issue сделал, но проект старый и заброшенный
# https://github.com/barseghyanartur/transliterate/issues/73
# также, этот модуль транслитерирует криво. й в j, например. Короче, лучше без него


# Движок: имена файлов, ID3-теги, обработка папки.


import os
import re
import sys
import unicodedata
import random
import threading
import traceback
import shutil
import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Set, List, Any, Callable

# Таблицы транслитерации (часть 1 из 4).
from music_transliterate_tables import TransliterationTablesMixin


# --- Определение болгарского языка -------------------------------------------
# Болгарский и русский различаются всего четырьмя парами букв:
#   х -> h / kh,  щ -> sht / shch,  ъ -> a / ',  ь -> y / '
# Поэтому язык важно определять только тогда, когда в тексте есть эти буквы.

# В русском твёрдый знак стоит только перед этими буквами
# ("съезд", "объявление", "съёмка", "адъютант"), а в дореформенной
# стилизации — ещё перед "и" ("Безъимянная").
HARD_SIGN_RUSSIAN_LETTERS = 'еёюяи'

# Букв ы/э/ё нет в болгарском алфавите: если они есть, текст не болгарский.
RUSSIAN_ONLY_LETTERS = 'ыэё'

# Буквы і/ї/є/ґ есть только в украинском: такой текст тоже не болгарский
# (иначе украинское "ще" = "ещё/будет" уводило бы названия в болгарский).
UKRAINIAN_LETTERS = 'іїєґ'

# Болгарские слова, которых нет в русском. Нужны для названий без "ъ"
# (по нему язык определяется однозначно), но с "щ"/"х"/"ь": "Щастие",
# "Още малко", "Хубава си". В списке только слова с этими буквами —
# остальные ("това", "сега", "вчера") транслитерируются одинаково в обоих
# языках и только создавали бы ложные срабатывания ("Сега" = Sega).
# Слова, совпадающие с русскими (хора, храм, хотел, характер, защита,
# мощь, после, много, само, вече, вещи, вещ), сюда тоже не входят.
# Слова "ще" здесь нет: в украинском оно пишется так же и встречается
# в названиях гораздо чаще ("Скільки Ще", "Ти Ще Спиш").
BULGARIAN_WORDS = frozenset("""
още щастие щастлив щастлива щастливо щастливи
помощ помощта нощ нощта вещта поща пощата
площад площада площадът пещ пещта общо
хляб хляба хлябът хубав хубава хубаво хубави хайде
храна храната хиляда хиляди хижа хижата
актьор актьори шофьор шофьори режисьор режисьори диригьор
""".split())


# безопасная запись в stderr с обработкой ошибок кодировки
def safe_stderr_write(message: str) -> None:
    """Безопасная запись в stderr с обработкой ошибок кодировки."""
    try:
        sys.stderr.write(message)
    except UnicodeEncodeError:
        # Заменяем не-ASCII символы на их кодовые точки (формат \uXXXX)
        safe_message = message.encode('ascii', errors='backslashreplace').decode('ascii')
        sys.stderr.write(safe_message)
    except Exception:
        # Если и это не помогло, игнорируем
        pass
    finally:
        try:
            sys.stderr.flush()
        except Exception:
            pass


def safe_stdout_write(message: str) -> None:
    """Безопасная запись в stdout с обработкой ошибок кодировки."""
    try:
        sys.stdout.write(message)
    except UnicodeEncodeError:
        safe_message = message.encode('ascii', errors='backslashreplace').decode('ascii')
        sys.stdout.write(safe_message)
    except Exception:
        pass
    finally:
        try:
            sys.stdout.flush()
        except Exception:
            pass


class FileTransliterator(TransliterationTablesMixin):
    def __init__(self, cancel_event: Optional[threading.Event] = None):
        self.cancel_event = cancel_event
        
        # Таблицы транслитерации для разных языков
        self.transliteration_tables = self._create_transliteration_tables()
        
        # Специфические символы для определения языка (только для detect_language,
        # к таблицам транслитерации отношения не имеют).
        #
        # ВАЖНО: detect_language() не ищет "признаки языка", а считает, сколько
        # символов из каждого набора встретилось в тексте, и берёт максимум;
        # при равенстве побеждает язык, стоящий в словаре раньше (русский).
        #
        # Поэтому полные алфавиты здесь работают как УСИЛИТЕЛЬ, а не как признак.
        # У украинского набора перечислены все буквы, а не только уникальные
        # єґії: общие с русским буквы дают обоим наборам одинаковый вклад, а
        # исход решают именно уникальные буквы. Если оставить только єґії, то в
        # "Українська пісня" счёт будет 2 против 18 у русского — победит русский
        # (на этом падал тест). Полный набор даёт 20 против 18, и украинский
        # выигрывает. То есть полный алфавит не означает "украинский текст
        # состоит из этих букв", он лишь уравнивает вклад общих букв.
        #
        # Болгарского набора здесь нет: он был подмножеством русского (нет
        # ы/э/ё), поэтому не мог выиграть ни при каком тексте. Болгарский
        # определяется отдельно — см. _detect_bulgarian(): по "ъ" как гласной
        # и по словарю BULGARIAN_WORDS.
        self.language_specific_chars = {
            'russian': set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),
            'ukrainian': set('абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'),
            'polish': set('ąćęłńóśźż'),
            'german': set('äöüß'),
            'european': set('áàâãäåæçéèêëíìîïñóòôõöøœúùûüýÿ')
        }
        
        # Символы, недопустимые в именах файлов (для Windows, macOS, Linux)
        self.invalid_filename_chars = set(r'<>:"/\|?*')
        
        # Замены для недопустимых символов
        self.invalid_char_replacements = {
            '<': '_',
            '>': '_',
            ':': '_',
            '"': "'",  # Кавычки заменяем на апостроф
            '/': '_',
            '\\': '_',
            '|': '_',
            '?': '_',
            '*': '_'   # Звездочка -> подчеркивание
        }
        
        # Популярные ID3 теги для транслитерации (только текстовые теги)
        self.id3_text_tags_to_transliterate = [
            'TIT2',  # Название трека
            'TPE1',  # Исполнитель
            'TPE2',  # Альбомный исполнитель
            'TALB',  # Альбом
            'TCOM',  # Композитор
            'TCON',  # Жанр
            'TENC',  # Кодировщик (Encoded by)
            'TEXT',  # Автор текста
            'TFLT',  # Тип файла
            'TIT1',  # Группировка
            'TIT3',  # Подзаголовок/описание
            'TKEY',  # Тональность
            'TLAN',  # Язык
            'TMED',  # Тип носителя
            'TOAL',  # Оригинальный альбом
            'TOFN',  # Оригинальное имя файла
            'TOLY',  # Автор текста оригинала
            'TOPE',  # Оригинальный исполнитель
            'TOWN',  # Владелец
            'TPE3',  # Дирижер
            'TPE4',  # Аранжировщик
            'TPOS',  # Номер диска
            'TPUB',  # Издатель
            'TRCK',  # Номер трека
            'TRSN',  # Радиостанция
            'TRSO',  # Владелец радиостанции
            'TSOA',  # Альбомный порядок
            'TSOP',  # Исполнитель для сортировки
            'TSOT',  # Название для сортировки
            'TSRC',  # ISRC
            'TSSE',  # Настройки кодировщика (Software/Hardware)
            'TSST',  # Подзаголовок набора
        ]
        
        # Состояния обработки текущего файла (для подробного логирования при ошибках)
        self.file_state = {
            'original': None,           # исходное имя файла (как на диске)
            'raw_name': None,           # имя без расширения (после splitext)
            'cleaned_before': None,     # после _clean_decorative_symbols
            'transliterated': None,     # после транслитерации
            'sanitized': None,          # после sanitize_filename
            'final_name': None,         # итоговое имя с расширением
            'language': None,           # определённый язык
        }

    def _reset_file_state(self):
        """Сбрасывает сохранённые состояния перед обработкой нового файла."""
        for key in self.file_state:
            self.file_state[key] = None

    def _log_file_state_on_error(self):
        """Выводит все непустые состояния имени файла в stderr при возникновении ошибки."""
        sys.stdout.flush()  # гарантируем, что предыдущие успешные сообщения уже выведены
        safe_stderr_write("\n" + "=" * 70 + "\n")
        safe_stderr_write("ОШИБКА ПРИ ОБРАБОТКЕ ФАЙЛА. ИСТОРИЯ ИЗМЕНЕНИЙ ИМЕНИ:\n")
        safe_stderr_write("=" * 70 + "\n")

        if self.file_state['original'] is not None:
            safe_stderr_write(f"Исходное имя (с диска)   : {repr(self.file_state['original'])}\n")
        if self.file_state['raw_name'] is not None:
            safe_stderr_write(f"Имя без расширения       : {repr(self.file_state['raw_name'])}\n")
        if self.file_state['cleaned_before'] is not None:
            safe_stderr_write(f"После очистки (до транслит): {repr(self.file_state['cleaned_before'])}\n")
        if self.file_state['transliterated'] is not None:
            safe_stderr_write(f"После транслитерации      : {repr(self.file_state['transliterated'])}\n")
        if self.file_state['sanitized'] is not None:
            safe_stderr_write(f"После sanitize            : {repr(self.file_state['sanitized'])}\n")
        if self.file_state['final_name'] is not None:
            safe_stderr_write(f"Итоговое имя с расширением: {repr(self.file_state['final_name'])}\n")
        if self.file_state['language'] is not None:
            safe_stderr_write(f"Определённый язык         : {self.file_state['language']}\n")

        safe_stderr_write("=" * 70 + "\n")

    # Метод для удаления декоративных Unicode-символов
    def _clean_decorative_symbols(self, text: str, strict: bool = False) -> str:
        """
        Удаляет декоративные и нетекстовые символы, оставляя только буквы, цифры, пробелы и базовую пунктуацию.
        
        Параметры:
            text (str): исходная строка
            strict (bool): если True, оставляет только ASCII-символы (буквы, цифры, ограниченная пунктуация)
        
        Возвращает:
            str: очищенная строка
        """
        # 1. Нормализация Unicode (NFKC) – преобразует лигатуры, надстрочные символы, декоративные варианты в обычные ASCII-аналоги
        #    Например: ﬁ -> fi, ① -> 1, ℌ -> H, Ｃ -> C
        text = unicodedata.normalize('NFKC', text)
        
        # 2. Замена нелатинских цифр (арабских, тайских, деванагари и т.д.) на ASCII-цифры
        #    Используем unicodedata.decimal() для получения числового значения.
        digit_replaced_chars = []
        for ch in text:
            try:
                # Пытаемся получить десятичное значение символа (работает для всех цифровых символов Unicode)
                decimal_value = unicodedata.decimal(ch)
                # Заменяем на соответствующую ASCII-цифру
                digit_replaced_chars.append(str(decimal_value))
            except ValueError:
                # Не является десятичной цифрой – оставляем как есть
                digit_replaced_chars.append(ch)
        text = ''.join(digit_replaced_chars)
        
        # 3. Удаление комбинирующих диакритических знаков (акцентов, огласовок и т.д.)
        #    Нормализуем в NFD (декомпозиция) – все составные символы разбиваются на базовый символ + combining marks
        text = unicodedata.normalize('NFD', text)
        #    Удаляем все символы категории Mn (Non-spacing Mark) и Mc (Spacing Combining Mark)
        text = ''.join(ch for ch in text if unicodedata.category(ch) not in ('Mn', 'Mc'))
        #    После удаления диакритик можно снова нормализовать в NFC для компактности (опционально)
        text = unicodedata.normalize('NFC', text)
        
        # Определяем разрешённые категории символов (по первой букве категории Unicode)
        # L - буквы, N - цифры, Z - пробелы (Zs/Zl/Zp), P - пунктуация, S - символы (валюта и т.п.)
        # ВАЖНО: здесь именно первые буквы категорий, иначе пробелы (Zs) отбрасывались:
        # сравнение шло с 'Z', а в наборе стояло 'Zs'. Из-за этого из имён файлов
        # пропадали все пробелы, а нормализация пробелов ниже не срабатывала.
        allowed_categories = {'L', 'N', 'Z', 'P', 'S'} if not strict else {'L', 'N', 'Z'}
        
        # Символы пунктуации, разрешённые в строгом режиме (ASCII)
        allowed_punctuation = set('.,!?;:\'\"- _()[]{}#$')
        
        # Чёрный список конкретных кодовых точек (невидимые, управляющие, мешающие)
        forbidden_codepoints = {
            # Невидимые и управляющие
            0x200B,  # ZERO WIDTH SPACE
            0x200C,  # ZERO WIDTH NON-JOINER
            0x200D,  # ZERO WIDTH JOINER
            0x2060,  # WORD JOINER
            0x2061,  # FUNCTION APPLICATION
            0x2062,  # INVISIBLE TIMES
            0x2063,  # INVISIBLE SEPARATOR
            0x2064,  # INVISIBLE PLUS
            0x2065,  # INVISIBLE ASTERISK
            0x2066,  # LEFT-TO-RIGHT ISOLATE
            0x2067,  # RIGHT-TO-LEFT ISOLATE
            0x2068,  # FIRST STRONG ISOLATE
            0x2069,  # POP DIRECTIONAL ISOLATE
            0xFEFF,  # ZERO WIDTH NO-BREAK SPACE (BOM)
            0x00AD,  # SOFT HYPHEN (невидимый дефис)
            0x034F,  # COMBINING GRAPHEME JOINER
            0x061C,  # ARABIC LETTER MARK
            0x115F,  # HANGUL CHOSEONG FILLER
            0x1160,  # HANGUL JUNGSEONG FILLER
            0x17B4,  # KHMER VOWEL INHERENT AQ
            0x17B5,  # KHMER VOWEL INHERENT AA
            0x180E,  # MONGOLIAN VOWEL SEPARATOR
            0x200E,  # LEFT-TO-RIGHT MARK
            0x200F,  # RIGHT-TO-LEFT MARK
            0x202A,  # LEFT-TO-RIGHT EMBEDDING
            0x202B,  # RIGHT-TO-LEFT EMBEDDING
            0x202C,  # POP DIRECTIONAL FORMATTING
            0x202D,  # LEFT-TO-RIGHT OVERRIDE
            0x202E,  # RIGHT-TO-LEFT OVERRIDE
            # Декоративные и нежелательные символы
            0x00B0,  # DEGREE SIGN (°)
            0x00B4,  # ACUTE ACCENT (´) – обычно удаляется, но для надёжности
            0x00B8,  # CEDILLA (¸)
            0x00AF,  # MACRON (¯)
            0x00B7,  # MIDDLE DOT (·)
            0x2206,  # INCREMENT / DELTA (∆) – часто используется как символ "изменение"
            0x2211,  # N-ARY SUMMATION (∑)
            0x221E,  # INFINITY (∞)
            0x2248,  # ALMOST EQUAL TO (≈)
            0x2260,  # NOT EQUAL TO (≠)
            0x2264,  # LESS-THAN OR EQUAL TO (≤)
            0x2265,  # GREATER-THAN OR EQUAL TO (≥)
            # Декоративные круги, точки и геометрические фигуры
            0x25CF,  # BLACK CIRCLE (●)
            0x25CB,  # WHITE CIRCLE (○)
            0x25CE,  # BULLSEYE (◎)
            0x25A0,  # BLACK SQUARE (■)
            0x25A1,  # WHITE SQUARE (□)
            0x25B2,  # BLACK UP-POINTING TRIANGLE (▲)
            0x25B6,  # BLACK RIGHT-POINTING TRIANGLE (▶)
            0x25C0,  # BLACK LEFT-POINTING TRIANGLE (◀)
            0x25BC,  # BLACK DOWN-POINTING TRIANGLE (▼)            
            0xFFFD,  # REPLACEMENT CHARACTER (�) – появляется при ошибках декодирования
            # Можно добавить другие по мере обнаружения
        }
        
        # Диапазоны нежелательных декоративных символов (могут быть добавлены блоком)
        forbidden_ranges = [
            (0x02B0, 0x02FF),   # Spacing Modifier Letters (например, ˙ U+02D9)
            (0x0370, 0x03FF),   # Greek and Coptic (включает греческую точку · U+0387)
            (0x1F000, 0x1F02F), # Mahjong Tiles
            (0x1F0A0, 0x1F0FF), # Playing Cards
            (0x1F100, 0x1F1FF), # Enclosed Alphanumeric Supplement
            (0x1F200, 0x1F2FF), # Enclosed Ideographic Supplement
            (0x1F300, 0x1F5FF), # Miscellaneous Symbols and Pictographs (эмодзи)
            (0x1F600, 0x1F64F), # Emoticons
            (0x1F680, 0x1F6FF), # Transport and Map Symbols
            (0x1F700, 0x1F77F), # Alchemical Symbols
            (0x1F780, 0x1F7FF), # Geometric Shapes Extended
            (0x1F800, 0x1F8FF), # Supplemental Arrows-C
            (0x1F900, 0x1F9FF), # Supplemental Symbols and Pictographs
            (0x1FA00, 0x1FA6F), # Chess Symbols
            (0x1FA70, 0x1FAFF), # Symbols and Pictographs Extended-A
            (0x2600, 0x26FF),   # Miscellaneous Symbols
            (0x2700, 0x27BF),   # Dingbats
            (0xFE00, 0xFE0F),   # Variation Selectors
            (0x0600, 0x06FF),   # Arabic (включает декоративный ۩ U+06E9)
            (0x0E00, 0x0E7F),   # Thai (включает тайскую цифру ๑ U+0E51, но она уже заменена на ASCII-цифру ранее)
            (0x2000, 0x206F),   # General Punctuation (включает BULLET • U+2022)
            (0x2E00, 0x2E7F),   # Supplemental Punctuation
            (0x3000, 0x303F),   # CJK Symbols and Punctuation
            (0x3200, 0x32FF),   # Enclosed CJK Letters and Months
            (0x3300, 0x33FF),   # CJK Compatibility
            (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms
        ]
        
        # Категории Unicode, которые всегда запрещены (даже если их первая буква совпадает с разрешёнными)
        forbidden_categories = {'Cc', 'Cf', 'Co', 'Cn', 'Cs'}

        result_chars = []
        for ch in text:
            cp = ord(ch)
            
            # Проверка на вхождение в запрещённые диапазоны
            if any(start <= cp <= end for start, end in forbidden_ranges):
                continue
            
            # Проверка на вхождение в чёрный список конкретных точек
            if cp in forbidden_codepoints:
                continue
            
            # Проверка категории
            cat = unicodedata.category(ch)
            if cat in forbidden_categories:
                continue
            
            # Фильтрация по разрешённым категориям
            cat_prefix = cat[0]  # первая буква категории
            if cat_prefix not in allowed_categories:
                continue
            
            # В строгом режиме дополнительно проверяем, что символ ASCII (<= 127) и/или входит в разрешённую пунктуацию
            if strict:
                if cp <= 127:
                    if cat_prefix == 'P' and ch not in allowed_punctuation:
                        continue
                    # Для остальных ASCII-символов (L, N, Zs) пропускаем
                else:
                    # Не-ASCII символы в строгом режиме запрещены
                    continue
            
            result_chars.append(ch)
        
        # Собираем результат
        cleaned = ''.join(result_chars)
        
        # 4. Нормализация пробельных символов: заменяем любые пробельные последовательности (включая неразрывные) на одиночный пробел
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Удаляем пробелы в начале и конце
        cleaned = cleaned.strip()
        
        return cleaned

    def sanitize_filename(self, filename: str) -> str:
        """Очищает имя файла от недопустимых символов"""
        result_chars = []
        
        for char in filename:
            if char in self.invalid_filename_chars:
                # Заменяем недопустимые символы
                if char in self.invalid_char_replacements:
                    result_chars.append(self.invalid_char_replacements[char])
                else:
                    result_chars.append('_')  # На всякий случай заменяем на подчеркивание
            else:
                result_chars.append(char)
        
        result = ''.join(result_chars)
        
        return result
    
    def _detect_bulgarian(self, text_lower: str) -> bool:
        """Болгарский по твёрдому знаку или по словарю.

        В русском "ъ" — разделительный знак и стоит только перед е/ё/ю/я
        ("съезд", "объявление"), в болгарском — гласная ("път", "мъж", "сън").
        Поэтому "ъ" перед любой другой кириллической буквой означает болгарский.

        "ъ" в конце слова, перед разделителем или латиницей ничего не решает:
        в болгарском слова на "ъ" почти не заканчиваются, а в русском так
        иногда стилизуют названия ("Барнаулъ", "Пиздецъ").

        Если "ъ" нет, смотрим словарь BULGARIAN_WORDS — он нужен для названий
        вида "Щастие" или "Хубава си", где различие только в щ/х/ь.
        """
        if any(char in RUSSIAN_ONLY_LETTERS for char in text_lower):
            return False
        if any(char in UKRAINIAN_LETTERS for char in text_lower):
            return False

        for index, char in enumerate(text_lower):
            if char != 'ъ':
                continue
            next_char = (text_lower[index + 1]
                         if index + 1 < len(text_lower) else '')
            if not 'а' <= next_char <= 'я':
                # конец слова, разделитель или латиница — неоднозначно
                continue
            if next_char not in HARD_SIGN_RUSSIAN_LETTERS:
                return True

        words = re.findall(r'[а-яё]+', text_lower)
        return any(word in BULGARIAN_WORDS for word in words)

    def detect_language(self, text: str) -> Optional[str]:
        """Определяет язык по специфическим символам в тексте.

        Болгарский проверяется отдельно (см. _detect_bulgarian), потому что
        по алфавиту он неотличим от русского. Остальные языки сравниваются
        по количеству вхождений символов из language_specific_chars:
        побеждает максимум, при равенстве — первый в словаре (русский).
        Наборы намеренно содержат полные алфавиты: общие буквы дают
        одинаковый вклад, а исход решают уникальные (єґії против ыэё).
        Подробнее — в комментарии в __init__.
        """
        text_lower = text.lower()

        if self._detect_bulgarian(text_lower):
            return 'bulgarian'

        # Считаем количество специфических символов для каждого языка
        language_scores = {}
        
        for lang, chars in self.language_specific_chars.items():
            count = sum(1 for char in text_lower if char in chars)
            if count > 0:
                language_scores[lang] = count
        
        if not language_scores:
            return None
            
        # Возвращаем язык с максимальным количеством специфических символов
        return max(language_scores.items(), key=lambda x: x[1])[0]
    
    def transliterate_text(self, text: str, language: Optional[str] = None, check_ascii: bool = True, filename: str = "") -> Optional[str]:
        """Транслитерирует текст с учетом выбранного языка.
        filename - имя файла для вывода в сообщениях об ошибках."""
        if not language:
            language = self.detect_language(text)
            if not language:
                # Если язык не определен, используем общую европейскую таблицу
                language = 'european'

        transliteration_table = self.transliteration_tables[language]
        # Резерв для символов, которых нет в выбранной таблице: декоративный
        # слой (Small Caps, коптские буквы) и прочие европейские символы есть
        # только в европейской таблице, а она включает и русскую кириллицу.
        # Так имя «Път ǝ» остаётся болгарским («Pat e»), а не превращается
        # в русское («P't e»).
        fallback_table = (None if language == 'european'
                          else self.transliteration_tables['european'])
        result = self._apply_transliteration_table(
            text, transliteration_table, fallback_table)

        # Сохраняем результат транслитерации в состояние (если это имя файла)
        if filename:
            self.file_state['transliterated'] = result
        
        # Проверка на не-ASCII символы (только для имен файлов)
        if check_ascii:
            has_non_ascii, highlighted = self.has_non_ascii(result)
            if has_non_ascii:
                file_info = f" (файл: {filename})" if filename else ""
                # Безопасный вывод в stderr с заменой проблемных символов
                sys.stdout.flush()
                safe_stderr_write(f"Ошибка: после транслитерации остались не-ASCII символы{file_info}:\n")
                safe_stderr_write(f"Исходный текст: {repr(text)}\n")
                # Пытаемся записать highlighted, но если не получается, заменяем проблемные символы
                try:
                    safe_stderr_write(f"Транслитерированный: {repr(result)}\n")
                except Exception:
                    safe_highlighted = result.encode('ascii', errors='backslashreplace').decode('ascii')
                    safe_stderr_write(f"Транслитерированный (с заменой): {safe_highlighted}\n")
                # Дополнительно показываем, какие именно символы не-ASCII
                non_ascii_chars = [ch for ch in result if ord(ch) > 127]
                safe_stderr_write(f"Оставшиеся не-ASCII символы: {repr(''.join(non_ascii_chars))}\n")
                # Логируем состояние файла при ошибке
                self._log_file_state_on_error()
                return None

        return result

    def _apply_transliteration_table(self, text: str, table: Dict[str, str],
                                     fallback_table: Optional[Dict[str, str]] = None) -> str:
        """Переводит текст по одной таблице.

        Символ, которого нет в таблице, сначала ищется в fallback_table
        (европейская таблица с декоративным слоем), затем нормализуется
        (убираются диакритика и декоративные модификаторы), CJK заменяются
        на '#'.
        """
        result_chars = []

        for char in text:
            if char in table:
                result_chars.append(table[char])
            elif fallback_table is not None and char in fallback_table:
                result_chars.append(fallback_table[char])
            elif self._is_cjk(char):
                # Заменяем китайские, японские, корейские иероглифы на #
                result_chars.append('#')
            elif self._should_transliterate(char):
                # Пытаемся нормализовать символ
                try:
                    # Пробуем декомпозицию символа
                    decomposed = unicodedata.normalize('NFD', char)
                    # Убираем диакритические знаки
                    base_char = ''.join(c for c in decomposed if not unicodedata.combining(c))
                    if base_char and base_char != char:
                        result_chars.append(base_char)
                    else:
                        # Если нормализация не помогла, оставляем символ как есть
                        result_chars.append(char)
                except Exception:
                    result_chars.append(char)
            else:
                result_chars.append(char)

        return ''.join(result_chars)

    def _should_transliterate(self, char: str) -> bool:
        """Определяет, нужно ли транслитерировать символ"""
        # Если символ уже ASCII, не транслитерируем
        if ord(char) <= 127:
            return False
        
        # Проверяем, является ли символ буквой
        category = unicodedata.category(char)
        
        # Буквенные символы: L* категории
        if category.startswith('L'):
            return True
        
        # Символы пунктуации: P* категории
        if category.startswith('P'):
            return True
        
        # Символы символов (валюта и т.д.): S* категории
        if category.startswith('S'):
            return True
        
        # Числовые символы: N* категории (не ASCII цифры)
        if category.startswith('N') and ord(char) > 127:
            return True
        
        # Проверяем диапазоны Unicode для различных символов
        code = ord(char)
        
        # Общие диапазоны символов, которые нужно транслитерировать:
        # Диапазоны Unicode для различных символов
        ranges_to_transliterate = [
            (0x0080, 0x00FF),    # Latin-1 Supplement
            (0x0100, 0x017F),    # Latin Extended-A
            (0x0180, 0x024F),    # Latin Extended-B
            (0x0250, 0x02AF),    # IPA Extensions
            (0x02B0, 0x02FF),    # Spacing Modifier Letters
            (0x0300, 0x036F),    # Combining Diacritical Marks
            (0x0370, 0x03FF),    # Greek and Coptic
            (0x0400, 0x04FF),    # Cyrillic
            (0x0500, 0x052F),    # Cyrillic Supplement
            (0x0530, 0x058F),    # Armenian
            (0x0590, 0x05FF),    # Hebrew
            (0x0600, 0x06FF),    # Arabic
            (0x0700, 0x074F),    # Syriac
            (0x0750, 0x077F),    # Arabic Supplement
            (0x0780, 0x07BF),    # Thaana
            (0x07C0, 0x07FF),    # NKo
            (0x0800, 0x083F),    # Samaritan
            (0x0840, 0x085F),    # Mandaic
            (0x0860, 0x086F),    # Syriac Supplement
            (0x08A0, 0x08FF),    # Arabic Extended-A
            (0x0900, 0x097F),    # Devanagari
            (0x0980, 0x09FF),    # Bengali
            (0x0A00, 0x0A7F),    # Gurmukhi
            (0x0A80, 0x0AFF),    # Gujarati
            (0x0B00, 0x0B7F),    # Oriya
            (0x0B80, 0x0BFF),    # Tamil
            (0x0C00, 0x0C7F),    # Telugu
            (0x0C80, 0x0CFF),    # Kannada
            (0x0D00, 0x0D7F),    # Malayalam
            (0x0D80, 0x0DFF),    # Sinhala
            (0x0E00, 0x0E7F),    # Thai
            (0x0E80, 0x0EFF),    # Lao
            (0x0F00, 0x0FFF),    # Tibetan
            (0x1000, 0x109F),    # Myanmar
            (0x10A0, 0x10FF),    # Georgian
            (0x1100, 0x11FF),    # Hangul Jamo
            (0x1200, 0x137F),    # Ethiopic
            (0x1380, 0x139F),    # Ethiopic Supplement
            (0x13A0, 0x13FF),    # Cherokee
            (0x1400, 0x167F),    # Unified Canadian Aboriginal Syllabics
            (0x1680, 0x169F),    # Ogham
            (0x16A0, 0x16FF),    # Runic
            (0x1700, 0x171F),    # Tagalog
            (0x1720, 0x173F),    # Hanunoo
            (0x1740, 0x175F),    # Buhid
            (0x1760, 0x177F),    # Tagbanwa
            (0x1780, 0x17FF),    # Khmer
            (0x1800, 0x18AF),    # Mongolian
            (0x18B0, 0x18FF),    # Unified Canadian Aboriginal Syllabics Extended
            (0x1900, 0x194F),    # Limbu
            (0x1950, 0x197F),    # Tai Le
            (0x1980, 0x19DF),    # New Tai Lue
            (0x19E0, 0x19FF),    # Khmer Symbols
            (0x1A00, 0x1A1F),    # Buginese
            (0x1A20, 0x1AAF),    # Tai Tham
            (0x1AB0, 0x1AFF),    # Combining Diacritical Marks Extended
            (0x1B00, 0x1B7F),    # Balinese
            (0x1B80, 0x1BBF),    # Sundanese
            (0x1BC0, 0x1BFF),    # Batak
            (0x1C00, 0x1C4F),    # Lepcha
            (0x1C50, 0x1C7F),    # Ol Chiki
            (0x1C80, 0x1C8F),    # Cyrillic Extended-C
            (0x1C90, 0x1CBF),    # Georgian Extended
            (0x1CC0, 0x1CCF),    # Sundanese Supplement
            (0x1CD0, 0x1CFF),    # Vedic Extensions
            (0x1D00, 0x1D7F),    # Phonetic Extensions
            (0x1D80, 0x1DBF),    # Phonetic Extensions Supplement
            (0x1DC0, 0x1DFF),    # Combining Diacritical Marks Supplement
            (0x1E00, 0x1EFF),    # Latin Extended Additional
            (0x1F00, 0x1FFF),    # Greek Extended
            (0x2000, 0x206F),    # General Punctuation
            (0x2070, 0x209F),    # Superscripts and Subscripts
            (0x20A0, 0x20CF),    # Currency Symbols
            (0x20D0, 0x20FF),    # Combining Diacritical Marks for Symbols
            (0x2100, 0x214F),    # Letterlike Symbols
            (0x2150, 0x218F),    # Number Forms
            (0x2190, 0x21FF),    # Arrows
            (0x2200, 0x22FF),    # Mathematical Operators
            (0x2300, 0x23FF),    # Miscellaneous Technical
            (0x2400, 0x243F),    # Control Pictures
            (0x2440, 0x245F),    # Optical Character Recognition
            (0x2460, 0x24FF),    # Enclosed Alphanumerics
            (0x2500, 0x257F),    # Box Drawing
            (0x2580, 0x259F),    # Block Elements
            (0x25A0, 0x25FF),    # Geometric Shapes
            (0x2600, 0x26FF),    # Miscellaneous Symbols
            (0x2700, 0x27BF),    # Dingbats
            (0x27C0, 0x27EF),    # Miscellaneous Mathematical Symbols-A
            (0x27F0, 0x27FF),    # Supplemental Arrows-A
            (0x2800, 0x28FF),    # Braille Patterns
            (0x2900, 0x297F),    # Supplemental Arrows-B
            (0x2980, 0x29FF),    # Miscellaneous Mathematical Symbols-B
            (0x2A00, 0x2AFF),    # Supplemental Mathematical Operators
            (0x2B00, 0x2BFF),    # Miscellaneous Symbols and Arrows
            (0x2C00, 0x2C5F),    # Glagolitic
            (0x2C60, 0x2C7F),    # Latin Extended-C
            (0x2C80, 0x2CFF),    # Coptic
            (0x2D00, 0x2D2F),    # Georgian Supplement
            (0x2D30, 0x2D7F),    # Tifinagh
            (0x2D80, 0x2DDF),    # Ethiopic Extended
            (0x2DE0, 0x2DFF),    # Cyrillic Extended-A
            (0x2E00, 0x2E7F),    # Supplemental Punctuation
            (0x2E80, 0x2EFF),    # CJK Radicals Supplement
            (0x2F00, 0x2FDF),    # Kangxi Radicals
            (0x2FF0, 0x2FFF),    # Ideographic Description Characters
            (0x3000, 0x303F),    # CJK Symbols and Punctuation
            (0x3040, 0x309F),    # Hiragana
            (0x30A0, 0x30FF),    # Katakana
            (0x3100, 0x312F),    # Bopomofo
            (0x3130, 0x318F),    # Hangul Compatibility Jamo
            (0x3190, 0x319F),    # Kanbun
            (0x31A0, 0x31BF),    # Bopomofo Extended
            (0x31C0, 0x31EF),    # CJK Strokes
            (0x31F0, 0x31FF),    # Katakana Phonetic Extensions
            (0x3200, 0x32FF),    # Enclosed CJK Letters and Months
            (0x3300, 0x33FF),    # CJK Compatibility
            (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
            (0x4DC0, 0x4DFF),    # Yijing Hexagram Symbols
            (0x4E00, 0x9FFF),    # CJK Unified Ideographs
            (0xA000, 0xA48F),    # Yi Syllables
            (0xA490, 0xA4CF),    # Yi Radicals
            (0xA4D0, 0xA4FF),    # Lisu
            (0xA500, 0xA63F),    # Vai
            (0xA640, 0xA69F),    # Cyrillic Extended-B
            (0xA6A0, 0xA6FF),    # Bamum
            (0xA700, 0xA71F),    # Modifier Tone Letters
            (0xA720, 0xA7FF),    # Latin Extended-D
            (0xA800, 0xA82F),    # Syloti Nagri
            (0xA830, 0xA83F),    # Common Indic Number Forms
            (0xA840, 0xA87F),    # Phags-pa
            (0xA880, 0xA8DF),    # Saurashtra
            (0xA8E0, 0xA8FF),    # Devanagari Extended
            (0xA900, 0xA92F),    # Kayah Li
            (0xA930, 0xA95F),    # Rejang
            (0xA960, 0xA97F),    # Hangul Jamo Extended-A
            (0xA980, 0xA9DF),    # Javanese
            (0xA9E0, 0xA9FF),    # Myanmar Extended-B
            (0xAA00, 0xAA5F),    # Cham
            (0xAA60, 0xAA7F),    # Myanmar Extended-A
            (0xAA80, 0xAADF),    # Tai Viet
            (0xAAE0, 0xAAFF),    # Meetei Mayek Extensions
            (0xAB00, 0xAB2F),    # Ethiopic Extended-A
            (0xAB30, 0xAB6F),    # Latin Extended-E
            (0xAB70, 0xABBF),    # Cherokee Supplement
            (0xABC0, 0xABFF),    # Meetei Mayek
            (0xAC00, 0xD7AF),    # Hangul Syllables
            (0xD7B0, 0xD7FF),    # Hangul Jamo Extended-B
            (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
            (0xFB00, 0xFB4F),    # Alphabetic Presentation Forms
            (0xFB50, 0xFDFF),    # Arabic Presentation Forms-A
            (0xFE00, 0xFE0F),    # Variation Selectors
            (0xFE10, 0xFE1F),    # Vertical Forms
            (0xFE20, 0xFE2F),    # Combining Half Marks
            (0xFE30, 0xFE4F),    # CJK Compatibility Forms
            (0xFE50, 0xFE6F),    # Small Form Variants
            (0xFE70, 0xFEFF),    # Arabic Presentation Forms-B
            (0xFF00, 0xFFEF),    # Halfwidth and Fullwidth Forms
            (0xFFF0, 0xFFFF),    # Specials
        ]
        
        for start, end in ranges_to_transliterate:
            if start <= code <= end:
                return True
        
        return False

    def _is_cjk(self, char: str) -> bool:
        """Проверяет, является ли символ иероглифом CJK (китайским, японским, корейским)."""
        code = ord(char)
        # Основные диапазоны CJK:
        # 0x4E00-0x9FFF   CJK Unified Ideographs (основные китайские и японские иероглифы)
        # 0x3400-0x4DBF   CJK Unified Ideographs Extension A
        # 0x20000-0x2A6DF CJK Unified Ideographs Extension B (редко, но для полноты)
        # 0xAC00-0xD7AF   Hangul Syllables (корейские слоговые блоки)
        # 0x1100-0x11FF   Hangul Jamo (составные части корейских букв)
        # 0x3130-0x318F   Hangul Compatibility Jamo
        # 0xA960-0xA97F   Hangul Jamo Extended-A
        # 0xD7B0-0xD7FF   Hangul Jamo Extended-B
        # Также добавим Hiragana/Katakana (японские слоговые азбуки)
        # 0x3040-0x309F   Hiragana
        # 0x30A0-0x30FF   Katakana
        # 0xFF65-0xFF9F   Halfwidth Katakana
        return (
            (0x4E00 <= code <= 0x9FFF) or
            (0x3400 <= code <= 0x4DBF) or
            (0x20000 <= code <= 0x2A6DF) or
            (0xAC00 <= code <= 0xD7AF) or
            (0x1100 <= code <= 0x11FF) or
            (0x3130 <= code <= 0x318F) or
            (0xA960 <= code <= 0xA97F) or
            (0xD7B0 <= code <= 0xD7FF) or
            (0x3040 <= code <= 0x309F) or   # Hiragana
            (0x30A0 <= code <= 0x30FF) or   # Katakana
            (0xFF65 <= code <= 0xFF9F)      # Halfwidth Katakana
        )

    def has_non_ascii(self, text: str) -> Tuple[bool, str]:
        """Проверяет наличие не-ASCII символов и возвращает подсвеченную строку"""
        has_non_ascii = False
        highlighted_parts = []
        
        for char in text:
            if ord(char) > 127 and char.isprintable():
                has_non_ascii = True
                highlighted_parts.append(f'\033[93m{char}\033[0m')  # Желтый цвет
            else:
                highlighted_parts.append(char)
        
        return has_non_ascii, ''.join(highlighted_parts)

    def process_filename(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Обрабатывает имя файла: отделяет расширение, транслитерирует имя"""
        # Сбрасываем состояние и сохраняем исходное имя файла
        self._reset_file_state()
        self.file_state['original'] = filename

        try:
            # Разделяем имя файла и расширение
            name, ext = os.path.splitext(filename)
            self.file_state['raw_name'] = name
            
            # Определяем язык
            language = self.detect_language(name)
            if not language:
                language = 'european'
            self.file_state['language'] = language
            
            # Предварительно очищаем от декоративных символов, чтобы они не мешали транслитерации
            cleaned_before = self._clean_decorative_symbols(name)
            self.file_state['cleaned_before'] = cleaned_before
            
            # Транслитерируем имя с проверкой на не-ASCII
            # передаём имя файла для вывода в ошибках
            transliterated_name = self.transliterate_text(cleaned_before, language, check_ascii=True, filename=filename)
            # transliterate_text уже обновляет file_state['transliterated'] и вызывает _log_file_state_on_error при ошибке
            
            if transliterated_name is None:
                # Ошибка уже залогирована в transliterate_text, просто возвращаем None
                return None, None
            
            # Очищаем от недопустимых символов в имени файла
            sanitized_name = self.sanitize_filename(transliterated_name)
            self.file_state['sanitized'] = sanitized_name
            
            # Удаляем декоративные символы (повторно, для страховки)
            cleaned_name = self._clean_decorative_symbols(sanitized_name)
            
            # Проверка на пустое имя после очистки
            if not cleaned_name or cleaned_name.isspace():
                sys.stdout.flush()
                safe_stderr_write(f"Ошибка: после удаления декоративных символов имя файла стало пустым (исходный файл: {filename})\n")
                self._log_file_state_on_error()
                return None, None

            final_name = cleaned_name + ext
            self.file_state['final_name'] = final_name

            return final_name, language

        except Exception as e:
            sys.stdout.flush()
            safe_stderr_write(f"  ✗ Исключение при обработке имени файла '{filename}': {e}\n")
            traceback.print_exc(file=sys.stderr)
            self._log_file_state_on_error()
            return None, None

    def _get_tag_text(self, tag) -> Optional[str]:
        """Безопасно получает текстовое значение тега"""
        try:
            # Пытаемся получить текстовое значение разными способами
            if hasattr(tag, 'text'):
                # Для большинства текстовых тегов
                if isinstance(tag.text, list) and len(tag.text) > 0:
                    # Преобразуем первый элемент в строку
                    text_value = str(tag.text[0])
                    return text_value
                elif isinstance(tag.text, str):
                    return tag.text
                else:
                    # Пробуем просто преобразовать в строку
                    return str(tag.text)
            elif hasattr(tag, '__str__'):
                # Для других объектов просто используем строковое представление
                return str(tag)
            return None
        except Exception:
            return None

    def transliterate_mp3_tags(self, file_path: Path, language: Optional[str]) -> bool:
        """Транслитерирует ID3-теги MP3-файла. language=None - автоопределение для каждого тега."""
        try:
            # Пытаемся импортировать mutagen для работы с ID3-тегами
            from mutagen.id3 import ID3, ID3NoHeaderError
            from mutagen.mp3 import MP3
            from mutagen import MutagenError
            from mutagen.id3 import COMM, TXXX, USLT
        except ImportError:
            safe_stdout_write(f"  Предупреждение: библиотека mutagen не установлена. "
                              f"ID3-теги файла '{file_path.name}' не будут обработаны.\n")
            safe_stdout_write("  Установите mutagen: pip install mutagen\n")
            return False

        try:
            # Загружаем MP3 файл
            audio = MP3(file_path, ID3=ID3)
            
            # Если у файла нет ID3 тегов, создаем их
            if audio.tags is None:
                audio.add_tags()

            tags_modified = False
            
            # Получаем все теги перед обработкой
            all_tags = list(audio.tags.keys())
            safe_stdout_write(f"  Найдено тегов в файле: {len(all_tags)}\n")
            
            # Транслитерируем указанные ID3 теги
            for tag_name in self.id3_text_tags_to_transliterate:
                if self.cancel_event and self.cancel_event.is_set():
                    safe_stdout_write("  Прерывание по требованию пользователя\n")
                    return False
                if tag_name in audio.tags:
                    try:
                        tag = audio.tags[tag_name]
                        tag_value = self._get_tag_text(tag)
                        
                        if tag_value:
                            # Транслитерируем значение тега (без проверки на ASCII)
                            # передаём имя файла для вывода в ошибках
                            transliterated_value = self.transliterate_text(
                                tag_value, language, check_ascii=False, filename=file_path.name
                            )
                            
                            if transliterated_value and transliterated_value != tag_value:
                                # Вместо создания нового фрейма, обновляем текст существующего фрейма
                                # Сохраняем все атрибуты тега
                                original_encoding = tag.encoding if hasattr(tag, 'encoding') else 3
                                # Обновляем текст тега
                                tag.text = [transliterated_value]
                                tags_modified = True
                                safe_stdout_write(f"    Обновлен тег {tag_name}: {tag_value[:50]}... -> {transliterated_value[:50]}...\n")
                    except Exception as e:
                        safe_stderr_write(f"  Ошибка при обработке тега {tag_name} в файле '{file_path.name}': {e}\n")
                        continue
            
            # Также транслитерируем COMM теги (комментарии)
            comm_tags = [tag_name for tag_name in all_tags if tag_name.startswith('COMM')]
            for tag_name in comm_tags:
                try:
                    tag = audio.tags[tag_name]
                    if isinstance(tag, COMM):
                        # Получаем текст комментария
                        if hasattr(tag, 'text'):
                            # Комментарий может иметь несколько частей, берем первую
                            if isinstance(tag.text, list) and len(tag.text) > 0:
                                comment_text = str(tag.text[0])
                            else:
                                comment_text = str(tag.text)
                            
                            if comment_text:
                                # Передаём имя файла для вывода в ошибках
                                transliterated_text = self.transliterate_text(
                                    comment_text, language, check_ascii=False, filename=file_path.name
                                )
                                if transliterated_text and transliterated_text != comment_text:
                                    # Обновляем текст комментария, сохраняя все остальные атрибуты
                                    tag.text = [transliterated_text]
                                    tags_modified = True
                                    safe_stdout_write(f"    Обновлен комментарий: {comment_text[:50]}... -> {transliterated_text[:50]}...\n")
                except Exception as e:
                    safe_stderr_write(f"  Ошибка при обработке комментария {tag_name} в файле '{file_path.name}': {e}\n")
                    continue
            
            # Обработка пользовательских тегов (TXXX)
            txxx_tags = [tag_name for tag_name in all_tags if tag_name.startswith('TXXX')]
            for tag_name in txxx_tags:
                try:
                    tag = audio.tags[tag_name]
                    if isinstance(tag, TXXX):
                        # Получаем текст пользовательского тега
                        if hasattr(tag, 'text'):
                            if isinstance(tag.text, list) and len(tag.text) > 0:
                                txxx_text = str(tag.text[0])
                            else:
                                txxx_text = str(tag.text)
                            
                            if txxx_text:
                                # Передаём имя файла для вывода в ошибках
                                transliterated_text = self.transliterate_text(
                                    txxx_text, language, check_ascii=False, filename=file_path.name
                                )
                                if transliterated_text and transliterated_text != txxx_text:
                                    # Обновляем текст тега, сохраняя описание и кодировку
                                    tag.text = [transliterated_text]
                                    tags_modified = True
                                    desc = tag.desc if hasattr(tag, 'desc') else ''
                                    safe_stdout_write(f"    Обновлен пользовательский тег '{desc}': {txxx_text[:50]}... -> {transliterated_text[:50]}...\n")
                except Exception as e:
                    safe_stderr_write(f"  Ошибка при обработке пользовательского тега {tag_name} в файле '{file_path.name}': {e}\n")
                    continue
            
            # Также обрабатываем теги текстов песен (USLT)
            uslt_tags = [tag_name for tag_name in all_tags if tag_name.startswith('USLT')]
            for tag_name in uslt_tags:
                try:
                    tag = audio.tags[tag_name]
                    if isinstance(tag, USLT):
                        # Получаем текст песни
                        if hasattr(tag, 'text'):
                            uslt_text = tag.text
                            if uslt_text:
                                # Передаём имя файла для вывода в ошибках
                                transliterated_text = self.transliterate_text(
                                    uslt_text, language, check_ascii=False, filename=file_path.name
                                )
                                if transliterated_text and transliterated_text != uslt_text:
                                    # Обновляем текст песни
                                    tag.text = transliterated_text
                                    tags_modified = True
                                    safe_stdout_write(f"    Обновлен текст песни: {len(uslt_text)} символов -> {len(transliterated_text)} символов\n")
                except Exception as e:
                    safe_stderr_write(f"  Ошибка при обработке текста песни {tag_name} в файле '{file_path.name}': {e}\n")
                    continue
            
            # Сохраняем изменения, если они были
            if tags_modified:
                try:
                    audio.save()
                    safe_stdout_write(f"  ✓ ID3-теги файла '{file_path.name}' транслитерированы и сохранены\n")
                    return True
                except Exception as e:
                    safe_stderr_write(f"  ✗ Ошибка при сохранении тегов файла '{file_path.name}': {e}\n")
                    return False
            else:
                safe_stdout_write(f"  - ID3-теги файла '{file_path.name}' не требуют изменений\n")
                return True

        except (ID3NoHeaderError, MutagenError) as e:
            safe_stderr_write(f"  ! Ошибка при чтении ID3-тегов файла '{file_path.name}': {e}\n")
            return False
        except Exception as e:
            safe_stderr_write(f"  ! Неожиданная ошибка при обработке ID3-тегов файла '{file_path.name}': {e}\n")
            traceback.print_exc(file=sys.stderr)
            return False

    def _dedupe_name(self, name: str, out_dir: Optional[Path], used_names: Set[str]) -> str:
        """Возвращает name или name (1), name (2), ... если имя занято."""
        def is_taken(n: str) -> bool:
            if n in used_names:
                return True
            if out_dir is not None and (out_dir / n).exists():
                return True
            return False

        if not is_taken(name):
            return name
        stem, ext = os.path.splitext(name)
        counter = 1
        while True:
            candidate = f"{stem} ({counter}){ext}"
            if not is_taken(candidate):
                return candidate
            counter += 1

    def process_directory(self, directory_path: str, testonly: bool = False,
                          process_id3: bool = True,
                          output_dir: Optional[str] = None,
                          used_names: Optional[Set[str]] = None,
                          transliterate_names: bool = True,
                          recursive: bool = False,
                          progress_callback: Optional[Callable[[int, int], None]] = None
                          ) -> Tuple[bool, List[Tuple[Path, Path]]]:
        """Обрабатывает файлы директории.

        output_dir=None  -> переименование на месте (или только ID3-обработка,
                              если transliterate_names=False).
        output_dir=<путь> -> копирование в output_dir, без изменения исходников.
        transliterate_names=False -> имена файлов не трогаем, только копируем/обрабатываем ID3.
        recursive=True -> обрабатывать и вложенные папки.

        Возвращает (success, [(source_path, target_path), ...]).
        """
        path = Path(directory_path)

        if not path.exists():
            safe_stderr_write(f"Ошибка: путь '{directory_path}' не существует\n")
            return False, []
        if not path.is_dir():
            safe_stderr_write(f"Ошибка: '{directory_path}' не является директорией\n")
            return False, []

        out_path = Path(output_dir) if output_dir else None
        if out_path is not None and not testonly:
            try:
                out_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                safe_stderr_write(f"Ошибка создания папки результата '{output_dir}': {e}\n")
                return False, []

        if used_names is None:
            used_names = set()

        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]

        if not files:
            safe_stdout_write(f"Директория '{directory_path}' не содержит файлов\n")
            return True, []

        safe_stdout_write(f"Найдено {len(files)} файлов для обработки\n\n")

        total = len(files)
        processed_files: Dict[str, Tuple[str, Optional[str], Path, Path]] = {}

        for idx, file_path in enumerate(files):
            if self.cancel_event and self.cancel_event.is_set():
                safe_stdout_write("\nОбработка отменена пользователем\n")
                return False, []
            if progress_callback and out_path is None:
                try:
                    progress_callback(idx + 1, total)
                except Exception:
                    pass

            original_name = file_path.name
            safe_stdout_write(f"Обработка файла: {original_name}\n")
            if testonly:
                safe_stdout_write(f"  [ТЕСТ] Полный путь: {file_path}\n")
            sys.stdout.flush()

            if transliterate_names:
                try:
                    result = self.process_filename(original_name)
                except Exception as e:
                    sys.stdout.flush()
                    safe_stderr_write(f"  ✗ Непредвиденная ошибка при обработке имени файла "
                                      f"'{original_name}': {e}\n")
                    self._log_file_state_on_error()
                    return False, []

                if result[0] is None:
                    return False, []
                new_name, language = result
                safe_stdout_write(f"  Определен язык: {language if language else 'не определен'}\n")
                safe_stdout_write(f"  Новое имя: {new_name}\n")
            else:
                new_name = original_name
                language = None

            if out_path is not None:
                deduped = self._dedupe_name(new_name, out_path, used_names)
                used_names.add(deduped)
                if deduped != new_name:
                    safe_stdout_write(f"  Имя скорректировано, чтобы избежать конфликта: {deduped}\n")
                target_path = out_path / deduped
                processed_files[str(file_path)] = (deduped, language, file_path, target_path)
            else:
                new_path = file_path.parent / new_name
                if new_name in [n for n, _, _, _ in processed_files.values()]:
                    sys.stdout.flush()
                    safe_stderr_write(f"  ✗ Ошибка: конфликт имен при переименовании:\n")
                    safe_stderr_write(f"  Файл '{original_name}' должен быть переименован в '{new_name}'\n")
                    safe_stderr_write(f"  Но файл с таким именем уже будет создан из другого исходного файла\n")
                    return False, []
                if new_path.exists() and new_path != file_path:
                    sys.stdout.flush()
                    safe_stderr_write(f"  ✗ Ошибка: файл '{new_name}' уже существует в директории\n")
                    safe_stderr_write(f"  Не удалось переименовать '{original_name}'\n")
                    return False, []
                processed_files[str(file_path)] = (new_name, language, file_path, new_path)

            safe_stdout_write(f"  ✓ Файл готов к обработке\n\n")
            sys.stdout.flush()

        if testonly:
            safe_stdout_write("=" * 50 + "\n")
            safe_stdout_write("ТЕСТОВЫЙ РЕЖИМ: реальные переименования и изменения тегов НЕ выполняются.\n")
            safe_stdout_write("Были бы выполнены следующие действия:\n")
            results: List[Tuple[Path, Path]] = []
            for key, (new_name, language, file_path, target_path) in processed_files.items():
                original_name = file_path.name
                if out_path is not None:
                    safe_stdout_write(f"  Копирование: '{file_path}' -> '{target_path}'\n")
                elif file_path.name != new_name:
                    safe_stdout_write(f"  Переименование: '{original_name}' -> '{new_name}'\n")
                if process_id3 and file_path.suffix.lower() == '.mp3':
                    safe_stdout_write(f"    Транслитерация ID3-тегов в файле (после копирования/переименования)\n")
                results.append((file_path, target_path))
            safe_stdout_write("=" * 50 + "\n")
            return True, results

        safe_stdout_write("=" * 50 + "\n")
        safe_stdout_write("Начинаю переименование/копирование файлов...\n")

        results = []
        for idx, (key, (new_name, language, file_path, target_path)) in enumerate(processed_files.items()):
            if self.cancel_event and self.cancel_event.is_set():
                safe_stdout_write("\nОбработка отменена пользователем\n")
                return False, results
            if progress_callback and out_path is not None:
                try:
                    progress_callback(idx + 1, total)
                except Exception:
                    pass

            original_name = file_path.name
            try:
                if out_path is not None:
                    shutil.copy2(file_path, target_path)
                    safe_stdout_write(f"✓ Скопирован: '{original_name}' -> '{new_name}'\n")
                else:
                    if file_path != target_path:
                        file_path.rename(target_path)
                        safe_stdout_write(f"✓ Переименован: '{original_name}' -> '{new_name}'\n")
                    else:
                        safe_stdout_write(f"- Файл '{original_name}' не требует переименования\n")

                if process_id3 and target_path.suffix.lower() == '.mp3':
                    safe_stdout_write(f"  Обработка ID3-тегов MP3-файла...\n")
                    self.transliterate_mp3_tags(target_path, language)
                    safe_stdout_write("\n")
                else:
                    safe_stdout_write("\n")

                results.append((file_path, target_path))
            except Exception as e:
                safe_stderr_write(f"✗ Ошибка при обработке файла '{original_name}': {e}\n")
                return False, results

        return True, results
