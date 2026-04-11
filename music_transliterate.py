# https://github.com/mtxadmin/music_transliterate/
# Many thanks to Deepseek AI, who greatly helped with writing and debugging of this script



# модуль transliterate - херня, детектит всё как ru. Issue сделал, но проект старый и заброшенный
# https://github.com/barseghyanartur/transliterate/issues/73
# также, этот модуль транслитерирует криво. й в j, например. Короче, лучше без него



import os
import re
import sys
import unicodedata
import random
from pathlib import Path
from typing import Dict, Optional, Tuple, Set, List, Any

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
        sys.stderr.flush()

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
        sys.stdout.flush()


class FileTransliterator:
    def __init__(self):
        # Таблицы транслитерации для разных языков
        self.transliteration_tables = self._create_transliteration_tables()
        
        # Специфические символы для определения языка
        self.language_specific_chars = {
            'russian': set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),
            'ukrainian': set('абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'),
            'polish': set('ąćęłńóśźż'),
            'bulgarian': set('абвгдежзийклмнопрстуфхцчшщъьюя'),
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

    def _add_extra_cyrillic(self, table: Dict[str, str]) -> None:
        """Добавляет в таблицу транслитерации символы расширенной кириллицы."""
        extra_cyrillic = {
            # Азербайджанский, башкирский, казахский, татарский и др.
            'Ә': 'A', 'ә': 'a',      # A with diaeresis (азерб., башк., каз., тат.)
            'Ғ': 'G', 'ғ': 'g',      # G with stroke (башк., каз., тадж., тат., уйг.)
            'Ҙ': 'Z', 'ҙ': 'z',      # Z with descender (башк.)
            'Ҡ': 'K', 'ҡ': 'k',      # K with descender (башк.)
            'Ң': 'N', 'ң': 'n',      # N with descender (башк., каз., кирг., тат., уйг.)
            'Ө': 'O', 'ө': 'o',      # O with bar (башк., бурят., калм., каз., монг., тат., тув., якут.)
            'Ү': 'U', 'ү': 'u',      # U with straight stroke (башк., бурят., калм., каз., кирг., монг., тат., тув., якут.)
            'Һ': 'H', 'һ': 'h',      # Shha (башк., бурят., калм., каз., тат., якут.)
            'Ҷ': 'Ch', 'ҷ': 'ch',    # Che with descender (тадж.)
            'Ҳ': 'H', 'ҳ': 'h',      # Ha with descender (тадж., узб.)
            'Қ': 'Q', 'қ': 'q',      # Ka with descender (каз., тадж., узб., уйг.)
            'Ӯ': 'U', 'ӯ': 'u',      # U with macron (тадж.)
            'Ғ': 'G', 'ғ': 'g',      # (повтор для единообразия)
            'Ҷ': 'J', 'ҷ': 'j',      # вариант транслитерации
            # Белорусский, украинский
            'Ў': 'U', 'ў': 'u',      # Short U (белорус., узб.)
            'І': 'I', 'і': 'i',      # Belarusian/Ukrainian I (уже есть в ukrainian_table)
            'Ґ': 'G', 'ґ': 'g',      # G with upturn (укр.)
            'Є': 'Ye', 'є': 'ye',    # Ukrainian Ye
            'Ї': 'Yi', 'ї': 'yi',    # Ukrainian Yi
            # Дополнительные буквы с диакритикой, встречающиеся в именах
            'Ӂ': 'Zh', 'ӂ': 'zh',    # Zhe with breve (молд., гагауз.)
            'Ӌ': 'Ch', 'ӌ': 'ch',    # Che with descender (хакас.)
            'Ӑ': 'A', 'ӑ': 'a',      # A with breve (чуваш.)
            'Ӗ': 'E', 'ӗ': 'e',      # E with breve (чуваш.)
            'Ҫ': 'S', 'ҫ': 's',      # Es with descender (башк., чуваш.)
            'Ҭ': 'T', 'ҭ': 't',      # Te with descender (абхаз.)
            'Ӳ': 'U', 'ӳ': 'u',      # U with double acute (чуваш.)
            'Ӱ': 'U', 'ӱ': 'u',      # U with diaeresis (алт., хакас., марийск.)
            'Ӹ': 'Y', 'ӹ': 'y',      # Yeru with diaeresis (марийск.)
            'Ӓ': 'A', 'ӓ': 'a',      # A with diaeresis (марийск., саам.)
            'Ӛ': 'E', 'ӛ': 'e',      # E with diaeresis (ненецк.)
            'Ӝ': 'Zh', 'ӝ': 'zh',    # Zhe with diaeresis (удм.)
            'Ӟ': 'Dz', 'ӟ': 'dz',    # Ze with diaeresis (удм.)
            'Ӥ': 'I', 'ӥ': 'i',      # I with diaeresis (удм.)
            'Ӧ': 'O', 'ӧ': 'o',      # O with diaeresis (коми, марийск., удм.)
            'Ӫ': 'O', 'ӫ': 'o',      # O with diaeresis and macron (эвенк.)
            'Ӭ': 'E', 'ӭ': 'e',      # E with diaeresis and macron (эвенк.)
            'Ӵ': 'Ch', 'ӵ': 'ch',    # Che with diaeresis (удм.)
            'Ҕ': 'G', 'ҕ': 'g',      # Ghe with middle hook (абхазский, якутский)
            'Ӄ': 'K', 'ӄ': 'k',      # Ka with vertical stroke (чукотский, корякский)
        }
        table.update(extra_cyrillic)

    def _add_decorative_latin(self, table: Dict[str, str]) -> None:
        """Добавляет в таблицу транслитерации декоративные латинские символы (Small Caps, коптские буквы и др.)."""
        decorative = {
            # Small Caps (U+1D00 – U+1D7F, выборочно)
            'ᴀ': 'A', 'ʙ': 'B', 'ᴄ': 'C', 'ᴅ': 'D', 'ᴇ': 'E',
            'ꜰ': 'F', 'ɢ': 'G', 'ʜ': 'H', 'ɪ': 'I', 'ᴊ': 'J',
            'ᴋ': 'K', 'ʟ': 'L', 'ᴍ': 'M', 'ɴ': 'N', 'ᴏ': 'O',
            'ᴘ': 'P', 'ꞯ': 'Q', 'ʀ': 'R', 'ꜱ': 'S', 'ᴛ': 'T',
            'ᴜ': 'U', 'ᴠ': 'V', 'ᴡ': 'W', 'x': 'X', 'ʏ': 'Y',
            'ᴢ': 'Z',
            # Latin Letter Yr (стилизованная R)
            'Ʀ': 'R',
            # Коптские буквы (часто используются для стилизации)
            'Ⲁ': 'A', 'ⲁ': 'a',
            'Ⲃ': 'B', 'ⲃ': 'b',
            'Ⲅ': 'G', 'ⲅ': 'g',
            'Ⲇ': 'D', 'ⲇ': 'd',
            'Ⲉ': 'E', 'ⲉ': 'e',
            'Ⲋ': 'S', 'ⲋ': 's',
            'Ⲍ': 'Z', 'ⲍ': 'z',
            'Ⲏ': 'I', 'ⲏ': 'i',
            'Ⲑ': 'Th', 'ⲑ': 'th',
            'Ⲓ': 'I', 'ⲓ': 'i',
            'Ⲕ': 'K', 'ⲕ': 'k',
            'Ⲗ': 'L', 'ⲗ': 'l',
            'Ⲙ': 'M', 'ⲙ': 'm',
            'Ⲛ': 'N', 'ⲛ': 'n',
            'Ⲝ': 'X', 'ⲝ': 'x',
            'Ⲟ': 'O', 'ⲟ': 'o',
            'Ⲡ': 'P', 'ⲡ': 'p',
            'Ⲣ': 'R', 'ⲣ': 'r',
            'Ⲥ': 'S', 'ⲥ': 's',
            'Ⲧ': 'T', 'ⲧ': 't',
            'Ⲩ': 'U', 'ⲩ': 'u',
            'Ⲫ': 'Ph', 'ⲫ': 'ph',
            'Ⲭ': 'Kh', 'ⲭ': 'kh',
            'Ⲯ': 'Ps', 'ⲯ': 'ps',
            'Ⲱ': 'O', 'ⲱ': 'o',
            'Ⲳ': 'Sh', 'ⲳ': 'sh',
            'Ⲵ': 'F', 'ⲵ': 'f',
            'Ⲷ': 'Kh', 'ⲷ': 'kh',
            'Ⲹ': 'H', 'ⲹ': 'h',
            'Ⲻ': 'Ch', 'ⲻ': 'ch',
            'Ⲽ': 'Ti', 'ⲽ': 'ti',
            # Декоративные буквы из других письменностей (похожие на латиницу)
            # Канадское слоговое письмо и чероки
            'ᗰ': 'M',   # U+15F0
            'Ꮌ': 'M',   # U+13BC (Cherokee)
            'Ꮗ': 'W',   # U+13C7 (Cherokee)
            'Ꭵ': 'i',   # U+13A5
            'Ꮢ': 'R',   # U+13D2
            # Грузинский (Mkhedruli) – визуально похожие на латиницу
            'ყ': 'y',   # U+10E7
            'მ': 'm',   # U+10DB
            'ნ': 'n',   # U+10DC
            'ა': 'a',   # U+10D0
            'ბ': 'b',   # U+10D1
            'გ': 'g',   # U+10D2
            'დ': 'd',   # U+10D3
            'ე': 'e',   # U+10D4
            'ვ': 'v',   # U+10D5
            'ზ': 'z',   # U+10D6
            'თ': 't',   # U+10D7
            'ი': 'i',   # U+10D8
            'კ': 'k',   # U+10D9
            'ლ': 'l',   # U+10DA
            'ო': 'o',   # U+10DD
            'პ': 'p',   # U+10DE
            'ჟ': 'zh',  # U+10DF
            'რ': 'r',   # U+10E0
            'ს': 's',   # U+10E1
            'ტ': 't',   # U+10E2
            'უ': 'u',   # U+10E3
            'ფ': 'p',   # U+10E4
            'ქ': 'k',   # U+10E5
            'ღ': 'gh',  # U+10E6
            'შ': 'sh',  # U+10E8
            'ჩ': 'ch',  # U+10E9
            'ც': 'ts',  # U+10EA
            'ძ': 'dz',  # U+10EB
            'წ': 'ts',  # U+10EC
            'ჭ': 'ch',  # U+10ED
            'ხ': 'kh',  # U+10EE
            'ჯ': 'j',   # U+10EF
            'ჰ': 'h',   # U+10F0
            # Греческие буквы (стилистические)
            'ϐ': 'b',   # U+03D0 (Greek beta symbol)
            # Тайские буквы (стилизация)
            'ค': 'a',   # U+0E04 (kho khwai, визуально 'a')
            # Гурмукхи (пенджаби)
            'ਮ': 'm',   # U+0A2E  # indents are ok here
            # Other
            'ʍ': 'w',   # U+028D LATIN SMALL LETTER TURNED W
            'ნ': 'n',   # U+10DC (уже добавлен выше, но оставлен для ясности)
        }
        table.update(decorative)

    def _create_transliteration_tables(self) -> Dict[str, Dict[str, str]]:
        """Создает таблицы транслитерации для всех языков"""
        
        # Русский язык по ГОСТ 7.79-2000 (система B) с изменениями:
        # - ъ -> '
        # - й -> y (вместо j)
        russian_table = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
            'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
            'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',  # Й -> Y
            'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
            'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
            'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': "'", 'Ы': 'Y', 'Ь': "'",
            'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',  # й -> y
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'shch', 'ъ': "'", 'ы': 'y', 'ь': "'",
            'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        # Украинский язык
        ukrainian_table = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Ґ': 'G', 'Д': 'D',
            'Е': 'E', 'Є': 'Ye', 'Ж': 'Zh', 'З': 'Z', 'И': 'Y', 'І': 'I',
            'Ї': 'Yi', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
            'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
            'Ь': "'", 'Ю': 'Yu', 'Я': 'Ya',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ґ': 'g', 'д': 'd',
            'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i',
            'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ь': "'", 'ю': 'yu', 'я': 'ya'
        }
        
        # Польский язык
        polish_table = {
            'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N',
            'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        
        # Болгарский язык
        bulgarian_table = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
            'Е': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y',
            'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
            'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh',
            'Щ': 'Sht', 'Ъ': 'A', 'Ь': 'Y', 'Ю': 'Yu', 'Я': 'Ya',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y',
            'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
            'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
            'щ': 'sht', 'ъ': 'a', 'ь': 'y', 'ю': 'yu', 'я': 'ya'
        }
        
        # Немецкий язык
        german_table = {
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue', 'ß': 'ss',
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue'
        }
        
        # Общая таблица для европейских языков с диакритикой и другими символами Unicode
        european_table = {
            # Latin-1 Supplement (ISO-8859-1)
            'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
            'Å': 'A', 'Æ': 'AE', 'Ç': 'C', 'È': 'E', 'É': 'E',
            'Ê': 'E', 'Ë': 'E', 'Ì': 'I', 'Í': 'I', 'Î': 'I',
            'Ï': 'I', 'Ð': 'D', 'Ñ': 'N', 'Ò': 'O', 'Ó': 'O',
            'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'Ø': 'O', 'Ù': 'U',
            'Ú': 'U', 'Û': 'U', 'Ü': 'U', 'Ý': 'Y', 'Þ': 'Th',
            'ß': 'ss', 'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a',
            'ä': 'a', 'å': 'a', 'æ': 'ae', 'ç': 'c', 'è': 'e',
            'é': 'e', 'ê': 'e', 'ë': 'e', 'ì': 'i', 'í': 'i',
            'î': 'i', 'ï': 'i', 'ð': 'd', 'ñ': 'n', 'ò': 'o',
            'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ý': 'y',
            'þ': 'th', 'ÿ': 'y',
            
            # Latin Extended-A (часть символов из Unicode диапазона U+0100-U+017F)
            'Ā': 'A', 'ā': 'a', 'Ă': 'A', 'ă': 'a', 'Ą': 'A',
            'ą': 'a', 'Ć': 'C', 'ć': 'c', 'Ĉ': 'C', 'ĉ': 'c',
            'Ċ': 'C', 'ċ': 'c', 'Č': 'C', 'č': 'c', 'Ď': 'D',
            'ď': 'd', 'Đ': 'D', 'đ': 'd', 'Ē': 'E', 'ē': 'e',
            'Ĕ': 'E', 'ĕ': 'e', 'Ė': 'E', 'ė': 'e', 'Ę': 'E',
            'ę': 'e', 'Ě': 'E', 'ě': 'e', 'Ĝ': 'G', 'ĝ': 'g',
            'Ğ': 'G', 'ğ': 'g', 'Ġ': 'G', 'ġ': 'g', 'Ģ': 'G',
            'ģ': 'g', 'Ĥ': 'H', 'ĥ': 'h', 'Ħ': 'H', 'ħ': 'h',
            'Ĩ': 'I', 'ĩ': 'i', 'Ī': 'I', 'ī': 'i', 'Ĭ': 'I',
            'ĭ': 'i', 'Į': 'I', 'į': 'i', 'İ': 'I', 'ı': 'i',
            'Ĵ': 'J', 'ĵ': 'j', 'Ķ': 'K', 'ķ': 'k', 'ĸ': 'k',
            'Ĺ': 'L', 'ĺ': 'l', 'Ļ': 'L', 'ļ': 'l', 'Ľ': 'L',
            'ľ': 'l', 'Ŀ': 'L', 'ŀ': 'l', 'Ł': 'L', 'ł': 'l',
            'Ń': 'N', 'ń': 'n', 'Ņ': 'N', 'ņ': 'n', 'Ň': 'N',
            'ň': 'n', 'ŉ': 'n', 'Ŋ': 'N', 'ŋ': 'n', 'Ō': 'O',
            'ō': 'o', 'Ŏ': 'O', 'ŏ': 'o', 'Ő': 'O', 'ő': 'o',
            'Œ': 'OE', 'œ': 'oe', 'Ŕ': 'R', 'ŕ': 'r', 'Ŗ': 'R',
            'ŗ': 'r', 'Ř': 'R', 'ř': 'r', 'Ś': 'S', 'ś': 's',
            'Ŝ': 'S', 'ŝ': 's', 'Ş': 'S', 'ş': 's', 'Š': 'S',
            'š': 's', 'Ţ': 'T', 'ţ': 't', 'Ť': 'T', 'ť': 't',
            'Ŧ': 'T', 'ŧ': 't', 'Ũ': 'U', 'ũ': 'u', 'Ū': 'U',
            'ū': 'u', 'Ŭ': 'U', 'ŭ': 'u', 'Ů': 'U', 'ů': 'u',
            'Ű': 'U', 'ű': 'u', 'Ų': 'U', 'ų': 'u', 'Ŵ': 'W',
            'ŵ': 'w', 'Ŷ': 'Y', 'ŷ': 'y', 'Ÿ': 'Y', 'Ź': 'Z',
            'ź': 'z', 'Ż': 'Z', 'ż': 'z', 'Ž': 'Z', 'ž': 'z',
            'ſ': 's',
            
            # Latin Extended-B (некоторые символы)
            'ƀ': 'b', 'Ɓ': 'B', 'Ƃ': 'B', 'ƃ': 'b', 'Ƅ': 'B',
            'ƅ': 'b', 'Ɔ': 'O', 'Ƈ': 'C', 'ƈ': 'c', 'Ɖ': 'D',
            'Ɗ': 'D', 'Ƌ': 'D', 'ƌ': 'd', 'ƍ': 'd', 'Ǝ': 'E',
            'Ə': 'E', 'Ɛ': 'E', 'Ƒ': 'F', 'ƒ': 'f', 'Ɠ': 'G',
            'Ɣ': 'G', 'ƕ': 'hv', 'Ɩ': 'I', 'Ɨ': 'I', 'Ƙ': 'K',
            'ƙ': 'k', 'ƚ': 'l', 'ƛ': 'l', 'Ɯ': 'M', 'Ɲ': 'N',
            'ƞ': 'n', 'Ɵ': 'O', 'Ơ': 'O', 'ơ': 'o', 'Ƣ': 'OI',
            'ƣ': 'oi', 'Ƥ': 'P', 'ƥ': 'p', 'Ʀ': 'R', 'Ƨ': 'S',
            'ƨ': 's', 'Ʃ': 'E', 'ƪ': 'E', 'ƫ': 't', 'Ƭ': 'T',
            'ƭ': 't', 'Ʈ': 'T', 'Ư': 'U', 'ư': 'u', 'Ʊ': 'Y',
            'Ʋ': 'V', 'Ƴ': 'Y', 'ƴ': 'y', 'Ƶ': 'Z', 'ƶ': 'z',
            'Ʒ': 'Z', 'Ƹ': 'Z', 'ƹ': 'z', 'ƺ': 'z', 'ƻ': '2',
            'Ƽ': '5', 'ƽ': '5', 'ƾ': 'T', 'ƿ': 'p',
            
            # Latin Extended Additional (некоторые символы)
            'Ḁ': 'A', 'ḁ': 'a', 'Ḃ': 'B', 'ḃ': 'b', 'Ḅ': 'B',
            'ḅ': 'b', 'Ḇ': 'B', 'ḇ': 'b', 'Ḉ': 'C', 'ḉ': 'c',
            'Ḋ': 'D', 'ḋ': 'd', 'Ḍ': 'D', 'ḍ': 'd', 'Ḏ': 'D',
            'ḏ': 'd', 'Ḑ': 'D', 'ḑ': 'd', 'Ḓ': 'D', 'ḓ': 'd',
            'Ḕ': 'E', 'ḕ': 'e', 'Ḗ': 'E', 'ḗ': 'e', 'Ḙ': 'E',
            'ḙ': 'e', 'Ḛ': 'E', 'ḛ': 'e', 'Ḝ': 'E', 'ḝ': 'e',
            'Ḟ': 'F', 'ḟ': 'f', 'Ḡ': 'G', 'ḡ': 'g', 'Ḣ': 'H',
            'ḣ': 'h', 'Ḥ': 'H', 'ḥ': 'h', 'Ḧ': 'H', 'ḧ': 'h',
            'Ḩ': 'H', 'ḩ': 'h', 'Ḫ': 'H', 'ḫ': 'h', 'Ḭ': 'I',
            'ḭ': 'i', 'Ḯ': 'I', 'ḯ': 'i', 'Ḱ': 'K', 'ḱ': 'k',
            'Ḳ': 'K', 'ḳ': 'k', 'Ḵ': 'K', 'ḵ': 'k', 'Ḷ': 'L',
            'ḷ': 'l', 'Ḹ': 'L', 'ḹ': 'l', 'Ḻ': 'L', 'ḻ': 'l',
            'Ḽ': 'L', 'ḽ': 'l', 'Ḿ': 'M', 'ḿ': 'm', 'Ṁ': 'M',
            'ṁ': 'm', 'Ṃ': 'M', 'ṃ': 'm', 'Ṅ': 'N', 'ṅ': 'n',
            'Ṇ': 'N', 'ṇ': 'n', 'Ṉ': 'N', 'ṉ': 'n', 'Ṋ': 'N',
            'ṋ': 'n', 'Ṍ': 'O', 'ṍ': 'o', 'Ṏ': 'O', 'ṏ': 'o',
            'Ṑ': 'O', 'ṑ': 'o', 'Ṓ': 'O', 'ṓ': 'o', 'Ṕ': 'P',
            'ṕ': 'p', 'Ṗ': 'P', 'ṗ': 'p', 'Ṙ': 'R', 'ṙ': 'r',
            'Ṛ': 'R', 'ṛ': 'r', 'Ṝ': 'R', 'ṝ': 'r', 'Ṟ': 'R',
            'ṟ': 'r', 'Ṡ': 'S', 'ṡ': 's', 'Ṣ': 'S', 'ṣ': 's',
            'Ṥ': 'S', 'ṥ': 's', 'Ṧ': 'S', 'ṧ': 's', 'Ṩ': 'S',
            'ṩ': 's', 'Ṫ': 'T', 'ṫ': 't', 'Ṭ': 'T', 'ṭ': 't',
            'Ṯ': 'T', 'ṯ': 't', 'Ṱ': 'T', 'ṱ': 't', 'Ṳ': 'U',
            'ṳ': 'u', 'Ṵ': 'U', 'ṵ': 'u', 'Ṷ': 'U', 'ṷ': 'u',
            'Ṹ': 'U', 'ṹ': 'u', 'Ṻ': 'U', 'ṻ': 'u', 'Ṽ': 'V',
            'ṽ': 'v', 'Ṿ': 'V', 'ṿ': 'v', 'Ẁ': 'W', 'ẁ': 'w',
            'Ẃ': 'W', 'ẃ': 'w', 'Ẅ': 'W', 'ẅ': 'w', 'Ẇ': 'W',
            'ẇ': 'w', 'Ẉ': 'W', 'ẉ': 'w', 'Ẋ': 'X', 'ẋ': 'x',
            'Ẍ': 'X', 'ẍ': 'x', 'Ẏ': 'Y', 'ẏ': 'y', 'Ẑ': 'Z',
            'ẑ': 'z', 'Ẓ': 'Z', 'ẓ': 'z', 'Ẕ': 'Z', 'ẕ': 'z',
            'ẖ': 'h', 'ẗ': 't', 'ẘ': 'w', 'ẙ': 'y', 'ẚ': 'a',
            'ẛ': 's', 'ẜ': 's', 'ẝ': 's', 'ẞ': 'SS', 'ẟ': 'd',
            
            # Latin Extended-C, D, E (некоторые символы)
            'ꞌ': "'", 'Ɥ': 'H', 'ꞎ': 'l', 'ꞏ': '.', 'Ꞑ': 'N',
            'ꞑ': 'n', 'Ꞓ': 'C', 'ꞓ': 'c', 'ꞔ': 'c', 'ꞕ': 'h',
            'Ꞗ': 'B', 'ꞗ': 'b', 'Ꞙ': 'F', 'ꞙ': 'f', 'Ꞛ': 'V',
            'ꞛ': 'v', 'Ꞝ': 'V', 'ꞝ': 'v', 'Ꞟ': 'V', 'ꞟ': 'v',
            
            # Дополнительные символы с диакритикой
            'Ȁ': 'A', 'ȁ': 'a', 'Ȃ': 'A', 'ȃ': 'a', 'Ȅ': 'E',
            'ȅ': 'e', 'Ȇ': 'E', 'ȇ': 'e', 'Ȉ': 'I', 'ȉ': 'i',
            'Ȋ': 'I', 'ȋ': 'i', 'Ȍ': 'O', 'ȍ': 'o', 'Ȏ': 'O',
            'ȏ': 'o', 'Ȑ': 'R', 'ȑ': 'r', 'Ȓ': 'R', 'ȓ': 'r',
            'Ȕ': 'U', 'ȕ': 'u', 'Ȗ': 'U', 'ȗ': 'u', 'Ș': 'S',
            'ș': 's', 'Ț': 'T', 'ț': 't', 'Ȝ': 'Y', 'ȝ': 'y',
            'Ȟ': 'H', 'ȟ': 'h', 'Ƞ': 'N', 'ȡ': 'd', 'Ȣ': 'OU',
            'ȣ': 'ou', 'Ȥ': 'Z', 'ȥ': 'z', 'Ȧ': 'A', 'ȧ': 'a',
            'Ȩ': 'E', 'ȩ': 'e', 'Ȫ': 'O', 'ȫ': 'o', 'Ȭ': 'O',
            'ȭ': 'o', 'Ȯ': 'O', 'ȯ': 'o', 'Ȱ': 'O', 'ȱ': 'o',
            'Ȳ': 'Y', 'ȳ': 'y',
            
            # Символы пунктуации и другие символы Unicode
            # Все кавычки заменяем строго на апостроф '
            '…': '...',   # HORIZONTAL ELLIPSIS (U+2026)
            '«': "'",     # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK (U+00AB) -> апостроф
            '»': "'",     # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK (U+00BB) -> апостроф
            '„': "'",     # DOUBLE LOW-9 QUOTATION MARK (U+201E) -> апостроф
            '“': "'",     # LEFT DOUBLE QUOTATION MARK (U+201C) -> апостроф
            '”': "'",     # RIGHT DOUBLE QUOTATION MARK (U+201D) -> апостроф
            '‘': "'",     # LEFT SINGLE QUOTATION MARK (U+2018) -> апостроф
            '’': "'",     # RIGHT SINGLE QUOTATION MARK (U+2019) -> апостроф
            '‹': "'",     # SINGLE LEFT-POINTING ANGLE QUOTATION MARK (U+2039) -> апостроф
            '›': "'",     # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK (U+203A) -> апостроф
            '–': '-',     # EN DASH (U+2013)
            '—': '-',     # EM DASH (U+2014)
            '―': '-',     # HORIZONTAL BAR (U+2015)
            '‒': '-',     # FIGURE DASH (U+2012)
            '−': '-',     # MINUS SIGN (U+2212)
            '±': '+/-',   # PLUS-MINUS SIGN (U+00B1)
            '×': 'x',     # MULTIPLICATION SIGN (U+00D7)
            '÷': '/',     # DIVISION SIGN (U+00F7)
            '©': '(c)',   # COPYRIGHT SIGN (U+00A9)
            '®': '(R)',   # REGISTERED SIGN (U+00AE)
            '™': '(TM)',  # TRADE MARK SIGN (U+2122)
            '°': 'deg',   # DEGREE SIGN (U+00B0)
            '№': 'No.',   # NUMERO SIGN (U+2116)
            '§': 'S.',    # SECTION SIGN (U+00A7)
            '¶': 'P.',    # PILCROW SIGN (U+00B6)
            '†': '+',     # DAGGER (U+2020)
            '‡': '++',    # DOUBLE DAGGER (U+2021)
            '•': '*',     # BULLET (U+2022)
            '·': '.',     # MIDDLE DOT (U+00B7)
            '¿': '?',     # INVERTED QUESTION MARK (U+00BF)
            '¡': '!',     # INVERTED EXCLAMATION MARK (U+00A1)
            '¦': '|',     # BROKEN BAR (U+00A6)
            '¬': '-',     # NOT SIGN (U+00AC)
            'µ': 'u',     # MICRO SIGN (U+00B5)
            '€': 'EUR',   # EURO SIGN (U+20AC)
            '£': 'GBP',   # POUND SIGN (U+00A3)
            '¥': 'JPY',   # YEN SIGN (U+00A5)
            '¢': 'cent',  # CENT SIGN (U+00A2)
            'ƒ': 'f',     # LATIN SMALL LETTER F WITH HOOK (U+0192)
            '‰': '%o',    # PER MILLE SIGN (U+2030)
            '‱': '%oo',   # PER TEN THOUSAND SIGN (U+2031)
            '‽': '?!',    # INTERROBANG (U+203D)
            '※': '*',     # REFERENCE MARK (U+203B)
            '⁂': '***',   # ASTERISM (U+2042)
            '⁇': '??',    # DOUBLE QUESTION MARK (U+2047)
            '⁈': '?!',    # QUESTION EXCLAMATION MARK (U+2048)
            '⁉': '!?',    # EXCLAMATION QUESTION MARK (U+2049)
            '⁊': '&',     # TIRONIAN SIGN ET (U+204A)
            '⁋': 'P',     # REVERSED PILCROW SIGN (U+204B)
            '⁌': '<',     # BLACK LEFTWARDS BULLET (U+204C)
            '⁍': '>',     # BLACK RIGHTWARDS BULLET (U+204D)
            
            # Математические символы
            '¼': '1/4',   # VULGAR FRACTION ONE QUARTER (U+00BC)
            '½': '1/2',   # VULGAR FRACTION ONE HALF (U+00BD)
            '¾': '3/4',   # VULGAR FRACTION THREE QUARTERS (U+00BE)
            '⅓': '1/3',   # VULGAR FRACTION ONE THIRD (U+2153)
            '⅔': '2/3',   # VULGAR FRACTION TWO THIRDS (U+2154)
            '⅕': '1/5',   # VULGAR FRACTION ONE FIFTH (U+2155)
            '⅖': '2/5',   # VULGAR FRACTION TWO FIFTHS (U+2156)
            '⅗': '3/5',   # VULGAR FRACTION THREE FIFTHS (U+2157)
            '⅘': '4/5',   # VULGAR FRACTION FOUR FIFTHS (U+2158)
            '⅙': '1/6',   # VULGAR FRACTION ONE SIXTH (U+2159)
            '⅚': '5/6',   # VULGAR FRACTION FIVE SIXTHS (U+215A)
            '⅛': '1/8',   # VULGAR FRACTION ONE EIGHTH (U+215B)
            '⅜': '3/8',   # VULGAR FRACTION THREE EIGHTHS (U+215C)
            '⅝': '5/8',   # VULGAR FRACTION FIVE EIGHTHS (U+215D)
            '⅞': '7/8',   # VULGAR FRACTION SEVEN EIGHTHS (U+215E)
            
            # Другие символы
            '★': '*',     # BLACK STAR (U+2605)
            '☆': '*',     # WHITE STAR (U+2606)
            '☺': ':)',    # WHITE SMILING FACE (U+263A)
            '☹': ':(',    # WHITE FROWNING FACE (U+2639)
            '♡': '<3',    # WHITE HEART SUIT (U+2661)
            '♥': '<3',    # BLACK HEART SUIT (U+2665)
            '♦': '<>',    # BLACK DIAMOND SUIT (U+2666)
            '♣': 'cl',    # BLACK CLUB SUIT (U+2663)
            '♠': 'sp',    # BLACK SPADE SUIT (U+2660)
            '✓': 'V',     # CHECK MARK (U+2713)
            '✔': 'V',     # HEAVY CHECK MARK (U+2714)
            '✗': 'X',     # BALLOT X (U+2717)
            '✘': 'X',     # HEAVY BALLOT X (U+2718)
            '○': 'O',     # WHITE CIRCLE (U+25CB)
            '●': 'O',     # BLACK CIRCLE (U+25CF)
            '◎': '(O)',   # BULLSEYE (U+25CE)
            '◇': '<>',    # WHITE DIAMOND (U+25C7)
            '◆': '<>',    # BLACK DIAMOND (U+25C6)
            '□': '[]',    # WHITE SQUARE (U+25A1)
            '■': '[]',    # BLACK SQUARE (U+25A0)
            '△': '/_\\',  # WHITE UP-POINTING TRIANGLE (U+25B3)
            '▲': '/_\\',  # BLACK UP-POINTING TRIANGLE (U+25B2)
            '▽': '\\_/',  # WHITE DOWN-POINTING TRIANGLE (U+25BD)
            '▼': '\\_/',  # BLACK DOWN-POINTING TRIANGLE (U+25BC)
            '→': '->',    # RIGHTWARDS ARROW (U+2192)
            '←': '<-',    # LEFTWARDS ARROW (U+2190)
            '↑': '^',     # UPWARDS ARROW (U+2191)
            '↓': 'v',     # DOWNWARDS ARROW (U+2193)
            '↔': '<->',   # LEFT RIGHT ARROW (U+2194)
            '↕': '^v',    # UP DOWN ARROW (U+2195)
            '↵': '<-',    # DOWNWARDS ARROW WITH CORNER LEFTWARDS (U+21B5)
            '⇄': '<->',   # RIGHTWARDS ARROW OVER LEFTWARDS ARROW (U+21C4)
            '⇅': '^v',    # UPWARDS ARROW LEFT OF DOWNWARDS ARROW (U+21C5)
            '⇆': '<->',   # LEFTWARDS ARROW OVER RIGHTWARDS ARROW (U+21C6)
            
            # Кириллические символы для других языков (не русский/украинский/болгарский)
            'Ђ': 'Dj',    # CYRILLIC CAPITAL LETTER DJE (U+0402) - сербский
            'ђ': 'dj',    # CYRILLIC SMALL LETTER DJE (U+0452) - сербский
            'Љ': 'Lj',    # CYRILLIC CAPITAL LETTER LJE (U+0409) - сербский/македонский
            'љ': 'lj',    # CYRILLIC SMALL LETTER LJE (U+0459) - сербский/македонский
            'Њ': 'Nj',    # CYRILLIC CAPITAL LETTER NJE (U+040A) - сербский/македонский
            'њ': 'nj',    # CYRILLIC SMALL LETTER NJE (U+045A) - сербский/македонский
            'Ћ': 'C',     # CYRILLIC CAPITAL LETTER TSHE (U+040B) - сербский
            'ћ': 'c',     # CYRILLIC SMALL LETTER TSHE (U+045B) - сербский
            'Џ': 'Dz',    # CYRILLIC CAPITAL LETTER DZHE (U+040F) - сербский/македонский
            'џ': 'dz',    # CYRILLIC SMALL LETTER DZHE (U+045F) - сербский/македонский
            'Ѕ': 'Dz',    # CYRILLIC CAPITAL LETTER DZE (U+0405) - македонский
            'ѕ': 'dz',    # CYRILLIC SMALL LETTER DZE (U+0455) - македонский
            'Ѣ': 'E',     # CYRILLIC CAPITAL LETTER YAT (U+0462) - старославянский
            'ѣ': 'e',     # CYRILLIC SMALL LETTER YAT (U+0463) - старославянский
            'Ѥ': 'Je',    # CYRILLIC CAPITAL LETTER IOTIFIED E (U+0464) - старославянский
            'ѥ': 'je',    # CYRILLIC SMALL LETTER IOTIFIED E (U+0465) - старославянский
            'Ѧ': 'Ja',    # CYRILLIC CAPITAL LETTER LITTLE YUS (U+0466) - старославянский
            'ѧ': 'ja',    # CYRILLIC SMALL LETTER LITTLE YUS (U+0467) - старославянский
            'Ѩ': 'Jja',   # CYRILLIC CAPITAL LETTER IOTIFIED LITTLE YUS (U+0468) - старославянский
            'ѩ': 'jja',   # CYRILLIC SMALL LETTER IOTIFIED LITTLE YUS (U+0469) - старославянский
            'Ѫ': 'O',     # CYRILLIC CAPITAL LETTER BIG YUS (U+046A) - старославянский
            'ѫ': 'o',     # CYRILLIC SMALL LETTER BIG YUS (U+046B) - старославянский
            'Ѭ': 'Jo',    # CYRILLIC CAPITAL LETTER IOTIFIED BIG YUS (U+046C) - старославянский
            'ѭ': 'jo',    # CYRILLIC SMALL LETTER IOTIFIED BIG YUS (U+046D) - старославянский
            'Ѯ': 'Ks',    # CYRILLIC CAPITAL LETTER KSI (U+046E) - старославянский
            'ѯ': 'ks',    # CYRILLIC SMALL LETTER KSI (U+046F) - старославянский
            'Ѱ': 'Ps',    # CYRILLIC CAPITAL LETTER PSI (U+0470) - старославянский
            'ѱ': 'ps',    # CYRILLIC SMALL LETTER PSI (U+0471) - старославянский
            'Ѳ': 'F',     # CYRILLIC CAPITAL LETTER FITA (U+0472) - старославянский
            'ѳ': 'f',     # CYRILLIC SMALL LETTER FITA (U+0473) - старославянский
            'Ѵ': 'I',     # CYRILLIC CAPITAL LETTER IZHITSA (U+0474) - старославянский
            'ѵ': 'i',     # CYRILLIC SMALL LETTER IZHITSA (U+0475) - старославянский
            'Ѷ': 'I',     # CYRILLIC CAPITAL LETTER IZHITSA WITH DOUBLE GRAVE ACCENT (U+0476) - старославянский
            'ѷ': 'i',     # CYRILLIC SMALL LETTER IZHITSA WITH DOUBLE GRAVE ACCENT (U+0477) - старославянский
        }
        
        # Добавляем расширенную кириллицу в русскую и европейскую таблицы
        self._add_extra_cyrillic(russian_table)
        self._add_extra_cyrillic(european_table)

        # Добавляем декоративные латинские и коптские символы в русскую (встречено in the wild) и европейскую таблицы
        self._add_decorative_latin(russian_table)
        self._add_decorative_latin(european_table)
        
        # Добавляем общие символы пунктуации ко всем таблицам
        # Все кавычки заменяем строго на апостроф, звездочки на подчеркивание
        common_punctuation = {
            '…': '...',   # Многоточие
            '–': '-',     # Длинное тире
            '—': '-',     # Длинное тире
            '«': "'",     # Левая кавычка -> апостроф
            '»': "'",     # Правая кавычка -> апостроф
            '„': "'",     # Нижняя кавычка -> апостроф
            '"': "'",     # Двойная кавычка -> апостроф
            '“': "'",     # Левая кавычка -> апостроф
            '”': "'",     # Правая кавычка -> апостроф
            '‘': "'",     # Левая одинарная кавычка -> апостроф
            '’': "'",     # Правая одинарная кавычка -> апостроф
            '‹': "'",     # Левая угловая кавычка -> апостроф
            '›': "'",     # Правая угловая кавычка -> апостроф
            '/': '_',     # Слэш -> подчеркивание
            '\\': '_',    # Обратный слэш -> подчеркивание
            ':': '_',     # Двоеточие -> подчеркивание
            '|': '_',     # Вертикальная черта -> подчеркивание
            '?': '_',     # Вопросительный знак -> подчеркивание
            '*': '_',     # Звездочка -> подчеркивание
            '<': '_',     # Меньше -> подчеркивание
            '>': '_',     # Больше -> подчеркивание
        }
        
        # Объединяем таблицы с общими символами пунктуации
        russian_table.update(common_punctuation)
        ukrainian_table.update(common_punctuation)
        polish_table.update(common_punctuation)
        bulgarian_table.update(common_punctuation)
        german_table.update(common_punctuation)
        
        # Для европейской таблицы добавляем еще больше символов
        european_table.update(common_punctuation)

        # Добавляем базовую кириллицу из русской таблицы в европейскую (встречается смесь)
        european_table.update(russian_table)
        
        return {
            'russian': russian_table,
            'ukrainian': ukrainian_table,
            'polish': polish_table,
            'bulgarian': bulgarian_table,
            'german': german_table,
            'european': european_table
        }
    
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
        # L - буквы, N - цифры, Zs - пробелы, P - пунктуация, S - символы (валюта и т.п.)
        allowed_categories = {'L', 'N', 'Zs', 'P', 'S'} if not strict else {'L', 'N', 'Zs'}
        
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
    
    def detect_language(self, text: str) -> Optional[str]:
        """Определяет язык по специфическим символам в тексте"""
        text_lower = text.lower()
        
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
        result_chars = []
        
        for char in text:
            if char in transliteration_table:
                result_chars.append(transliteration_table[char])
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
                except:
                    # Если произошла ошибка, оставляем символ как есть
                    result_chars.append(char)
            else:
                result_chars.append(char)
        
        result = ''.join(result_chars)
        
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
            import traceback
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
            else:
                return None
        except Exception:
            return None
    
    def transliterate_mp3_tags(self, file_path: Path, language: str) -> bool:
        """Транслитерирует ID3-теги MP3-файла"""
        try:
            # Пытаемся импортировать mutagen для работы с ID3-тегами
            from mutagen.id3 import ID3, ID3NoHeaderError
            from mutagen.mp3 import MP3
            from mutagen import MutagenError
            from mutagen.id3 import TextFrame, COMM, TXXX, USLT, APIC
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
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False
    
    def process_directory(self, directory_path: str) -> bool:
        """Обрабатывает все файлы в указанной директории"""
        path = Path(directory_path)
        
        if not path.exists():
            safe_stderr_write(f"Ошибка: путь '{directory_path}' не существует\n")
            return False
        
        if not path.is_dir():
            safe_stderr_write(f"Ошибка: '{directory_path}' не является директорией\n")
            return False
        
        # Собираем все файлы в директории
        files = [f for f in path.iterdir() if f.is_file()]
        
        if not files:
            safe_stdout_write(f"Директория '{directory_path}' не содержит файлов\n")
            return True
        
        safe_stdout_write(f"Найдено {len(files)} файлов для обработки\n\n")
        
        # Сначала проверяем все файлы на наличие проблем
        processed_files = {}
        
        for file_path in files:
            original_name = file_path.name
            safe_stdout_write(f"Обработка файла: {original_name}\n")
            sys.stdout.flush()
            
            try:
                result = self.process_filename(original_name)
            except Exception as e:
                sys.stdout.flush()
                safe_stderr_write(f"  ✗ Непредвиденная ошибка при обработке имени файла '{original_name}': {e}\n")
                self._log_file_state_on_error()
                return False
            
            if result[0] is None:
                # Ошибка уже залогирована в process_filename/transliterate_text
                return False
            
            new_name, language = result
            
            safe_stdout_write(f"  Определен язык: {language if language else 'не определен'}\n")
            safe_stdout_write(f"  Новое имя: {new_name}\n")
            
            # Проверяем на конфликт имен в пределах текущей обработки
            if new_name in [name for name, _, _ in processed_files.values()]:
                sys.stdout.flush()
                safe_stderr_write(f"  ✗ Ошибка: конфликт имен при переименовании:\n")
                safe_stderr_write(f"  Файл '{original_name}' должен быть переименован в '{new_name}'\n")
                safe_stderr_write(f"  Но файл с таким именем уже будет создан из другого исходного файла\n")
                return False
            
            # Проверяем, существует ли уже файл с таким именем
            new_path = file_path.parent / new_name
            if new_path.exists() and new_path != file_path:
                sys.stdout.flush()
                safe_stderr_write(f"  ✗ Ошибка: файл '{new_name}' уже существует в директории\n")
                safe_stderr_write(f"  Не удалось переименовать '{original_name}'\n")
                return False
            
            processed_files[original_name] = (new_name, language, file_path)
            safe_stdout_write(f"  ✓ Файл готов к переименованию\n\n")
            sys.stdout.flush()
        
        # Если все проверки пройдены, выполняем переименование
        safe_stdout_write("=" * 50 + "\n")
        safe_stdout_write("Начинаю переименование файлов...\n")
        
        for original_name, (new_name, language, file_path) in processed_files.items():
            old_path = file_path
            new_path = old_path.parent / new_name
            
            try:
                if old_path != new_path:
                    old_path.rename(new_path)
                    safe_stdout_write(f"✓ Переименован: '{original_name}' -> '{new_name}'\n")
                else:
                    safe_stdout_write(f"- Файл '{original_name}' не требует переименования\n")
                
                # Если файл MP3, транслитерируем ID3-теги
                if new_path.suffix.lower() == '.mp3':
                    safe_stdout_write(f"  Обработка ID3-тегов MP3-файла...\n")
                    self.transliterate_mp3_tags(new_path, language)
                    safe_stdout_write("\n")
                else:
                    safe_stdout_write("\n")
            except Exception as e:
                safe_stderr_write(f"✗ Ошибка при обработке файла '{original_name}': {e}\n")
                return False
        
        return True


def add_number_prefixes(directory, flag_ge_1000=False):
    """
    Добавляет к именам файлов в указанном каталоге случайные числовые префиксы.
    
    Параметры:
    directory (str): путь к каталогу с файлами
    flag_ge_1000 (bool): если True, префикс будет в диапазоне 1000-9999
    """
    
    # Проверяем существование каталога
    if not os.path.isdir(directory):
        raise ValueError(f"Каталог '{directory}' не существует")
    
    # Определяем диапазон случайных чисел
    min_value = 1000 if flag_ge_1000 else 1
    max_value = 9999
    
    # Регулярное выражение для поиска существующего префикса (4 цифры + пробел в начале)
    prefix_pattern = re.compile(r'^\d{4}\s')
    
    # Собираем все файлы в каталоге
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    
    if not files:
        safe_stdout_write(f"Каталог '{directory}' не содержит файлов\n")
        return
    
    safe_stdout_write(f"\n" + "=" * 50 + "\n")
    safe_stdout_write(f"Добавление числовых префиксов...\n")
    safe_stdout_write(f"Найдено {len(files)} файлов для добавления префиксов\n")
    safe_stdout_write(f"Диапазон префиксов: {min_value:04d}-{max_value:04d}\n\n")
    
    # Обрабатываем файлы в каталоге
    for filename in files:
        filepath = os.path.join(directory, filename)
        
        # Удаляем существующий префикс, если он есть
        new_name = filename
        if prefix_pattern.match(filename):
            # Удаляем первые 5 символов (4 цифры + пробел)
            new_name = filename[5:]
            safe_stdout_write(f"  Удален существующий префикс у файла: {filename}\n")
        
        # Генерируем случайный префикс
        random_number = random.randint(min_value, max_value)
        prefix = f"{random_number:04d} "
        
        # Формируем новое имя файла
        final_name = prefix + new_name
        
        # Переименовываем файл
        new_filepath = os.path.join(directory, final_name)
        try:
            os.rename(filepath, new_filepath)
            safe_stdout_write(f"✓ Добавлен префикс: {filename} -> {final_name}\n")
        except Exception as e:
            safe_stderr_write(f"✗ Ошибка при переименовании {filename}: {e}\n")


def process_directory_with_prefixes(directory_path: str, flag_ge_1000: bool = False):
    """
    Полный процесс обработки директории: транслитерация + добавление префиксов
    """
    transliterator = FileTransliterator()
    
    safe_stdout_write("=" * 70 + "\n")
    safe_stdout_write("НАЧАЛО ОБРАБОТКИ ДИРЕКТОРИИ\n")
    safe_stdout_write("=" * 70 + "\n")
    
    # Шаг 1: Транслитерация имен файлов и ID3-тегов
    safe_stdout_write("\n" + "=" * 50 + "\n")
    safe_stdout_write("ШАГ 1: ТРАНСЛИТЕРАЦИЯ ИМЕН ФАЙЛОВ И ID3-ТЕГОВ\n")
    safe_stdout_write("=" * 50 + "\n")
    
    try:
        success = transliterator.process_directory(directory_path)
        if not success:
            safe_stdout_write("\n" + "=" * 50 + "\n")
            safe_stdout_write("Транслитерация прервана из-за ошибок\n")
            return False
    except Exception as e:
        safe_stderr_write(f"\nОшибка при транслитерации: {e}\n")
        return False
    
    # Шаг 2: Добавление числовых префиксов
    safe_stdout_write("\n" + "=" * 50 + "\n")
    safe_stdout_write("ШАГ 2: ДОБАВЛЕНИЕ ЧИСЛОВЫХ ПРЕФИКСОВ\n")
    safe_stdout_write("=" * 50 + "\n")
    
    try:
        add_number_prefixes(directory_path, flag_ge_1000)
    except Exception as e:
        safe_stderr_write(f"\nОшибка при добавлении префиксов: {e}\n")
        return False
    
    return True


def main(directory_path, flag_ge_1000 = False):
    """Основная функция программы"""
    #if len(sys.argv) < 2:
    #    print("Использование:")
    #    print("  python transliterate_files.py <путь_к_директории> [--ge-1000] [--only-prefixes] [--only-transliterate]")
    #    print("\nОпции:")
    #    print("  --ge-1000          : Использовать префиксы в диапазоне 1000-9999 (по умолчанию: 1-9999)")
    #    print("  --only-prefixes    : Только добавить/изменить префиксы (без транслитерации)")
    #    print("  --only-transliterate: Только транслитерировать (без добавления префиксов)")
    #    sys.exit(1)
    
    #directory_path = sys.argv[1]
    
    if not directory_path:
        safe_stderr_write("Ошибка: путь не может быть пустым\n")
        sys.exit(1)
    
    # Проверяем флаги
    flag_ge_1000 = '--ge-1000' in sys.argv
    only_prefixes = '--only-prefixes' in sys.argv
    only_transliterate = '--only-transliterate' in sys.argv
    
    # Проверяем конфликт флагов
    if only_prefixes and only_transliterate:
        safe_stdout_write("Ошибка: нельзя одновременно использовать --only-prefixes и --only-transliterate\n")
        sys.exit(1)
    
    try:
        if only_prefixes:
            # Только добавление префиксов
            safe_stdout_write("=" * 70 + "\n")
            safe_stdout_write("РЕЖИМ: ТОЛЬКО ДОБАВЛЕНИЕ/ИЗМЕНЕНИЕ ПРЕФИКСОВ\n")
            safe_stdout_write("=" * 70 + "\n")
            add_number_prefixes(directory_path, flag_ge_1000)
            safe_stdout_write("\n" + "=" * 70 + "\n")
            safe_stdout_write("ДОБАВЛЕНИЕ ПРЕФИКСОВ ЗАВЕРШЕНО\n")
            safe_stdout_write("=" * 70 + "\n")
        
        elif only_transliterate:
            # Только транслитерация
            safe_stdout_write("=" * 70 + "\n")
            safe_stdout_write("РЕЖИМ: ТОЛЬКО ТРАНСЛИТЕРАЦИЯ\n")
            safe_stdout_write("=" * 70 + "\n")
            transliterator = FileTransliterator()
            success = transliterator.process_directory(directory_path)
            if success:
                safe_stdout_write("\n" + "=" * 70 + "\n")
                safe_stdout_write("ТРАНСЛИТЕРАЦИЯ ЗАВЕРШЕНА\n")
                safe_stdout_write("=" * 70 + "\n")
            else:
                safe_stdout_write("\n" + "=" * 70 + "\n")
                safe_stdout_write("ТРАНСЛИТЕРАЦИЯ ПРЕРВАНА ИЗ-ЗА ОШИБОК\n")
                safe_stdout_write("=" * 70 + "\n")
                sys.exit(1)
        
        else:
            # Полный процесс: транслитерация + добавление префиксов (режим по умолчанию)
            safe_stdout_write("=" * 70 + "\n")
            safe_stdout_write("РЕЖИМ: ПОЛНАЯ ОБРАБОТКА (ТРАНСЛИТЕРАЦИЯ + ПРЕФИКСЫ)\n")
            safe_stdout_write("=" * 70 + "\n")
            success = process_directory_with_prefixes(directory_path, flag_ge_1000)
            if success:
                safe_stdout_write("\n" + "=" * 70 + "\n")
                safe_stdout_write("ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!\n")
                safe_stdout_write("=" * 70 + "\n")
            else:
                safe_stdout_write("\n" + "=" * 70 + "\n")
                safe_stdout_write("ОБРАБОТКА ПРЕРВАНА ИЗ-ЗА ОШИБОК\n")
                safe_stdout_write("=" * 70 + "\n")
                sys.exit(1)
                
    except KeyboardInterrupt:
        safe_stderr_write("\n\nОбработка прервана пользователем\n")
        sys.exit(1)
    except Exception as e:
        safe_stderr_write(f"\nПроизошла непредвиденная ошибка: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
