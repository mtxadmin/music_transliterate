# https://github.com/mtxadmin/music_transliterate/
# Many thanks to Deepseek AI, who greatly helped with writing and debugging of this script



# модуль transliterate - херня, детектит всё как ru. Issue сделал, но проект старый и заброшенный
# https://github.com/barseghyanartur/transliterate/issues/73
# также, этот модуль транслитерирует криво. й в j, например. Короче, лучше без него



import os
import re
import sys
import unicodedata
from pathlib import Path
import random


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
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', ' ш': 'sh', 'щ': 'shch',
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
        
        # Общая таблица для европейских языков с диакритикой
        european_table = {
            # Latin-1 Supplement
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
            
            # Latin Extended-A
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
            'ſ': 's'
        }
        
        return {
            'russian': russian_table,
            'ukrainian': ukrainian_table,
            'polish': polish_table,
            'bulgarian': bulgarian_table,
            'german': german_table,
            'european': european_table
        }
    
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
    
    def transliterate_text(self, text: str, language: Optional[str] = None, check_ascii: bool = True) -> Optional[str]:
        """Транслитерирует текст с учетом выбранного языка"""
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
            elif language == 'european' and self._is_diacritic(char):
                # Для диакритических символов без явной таблицы используем нормализацию
                normalized = unicodedata.normalize('NFD', char)
                # Убираем диакритические знаки
                base_char = ''.join(c for c in normalized if not unicodedata.combining(c))
                result_chars.append(base_char if base_char else char)
            else:
                result_chars.append(char)
        
        result = ''.join(result_chars)
        
        # Проверка на не-ASCII символы (только для имен файлов)
        if check_ascii:
            has_non_ascii, highlighted = self.has_non_ascii(result)
            if has_non_ascii:
                print(f"Ошибка: после транслитерации остались не-ASCII символы:")
                print(f"Исходный текст: {text}")
                print(f"Транслитерированный: {highlighted}")
                return None
        
        return result
    
    def _is_diacritic(self, char: str) -> bool:
        """Проверяет, является ли символ диакритическим"""
        return unicodedata.category(char).startswith('L') and ord(char) > 127
    
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
        # Разделяем имя файла и расширение
        name, ext = os.path.splitext(filename)
        
        # Определяем язык
        language = self.detect_language(name)
        if not language:
            language = 'european'
        
        # Транслитерируем имя с проверкой на не-ASCII
        transliterated_name = self.transliterate_text(name, language, check_ascii=True)
        
        if transliterated_name is None:
            return None, None
        
        return transliterated_name + ext, language
    
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
            print(f"  Предупреждение: библиотека mutagen не установлена. "
                  f"ID3-теги файла '{file_path.name}' не будут обработаны.")
            print("  Установите mutagen: pip install mutagen")
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
            print(f"  Найдено тегов в файле: {len(all_tags)}")
            
            # Транслитерируем указанные ID3 теги
            for tag_name in self.id3_text_tags_to_transliterate:
                if tag_name in audio.tags:
                    try:
                        tag = audio.tags[tag_name]
                        tag_value = self._get_tag_text(tag)
                        
                        if tag_value:
                            # Транслитерируем значение тега (без проверки на ASCII)
                            transliterated_value = self.transliterate_text(
                                tag_value, language, check_ascii=False
                            )
                            
                            if transliterated_value and transliterated_value != tag_value:
                                # Вместо создания нового фрейма, обновляем текст существующего фрейма
                                # Сохраняем все атрибуты тега
                                original_encoding = tag.encoding if hasattr(tag, 'encoding') else 3
                                # Обновляем текст тега
                                tag.text = [transliterated_value]
                                tags_modified = True
                                print(f"    Обновлен тег {tag_name}: {tag_value[:50]}... -> {transliterated_value[:50]}...")
                    except Exception as e:
                        print(f"  Ошибка при обработке тега {tag_name}: {e}")
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
                                transliterated_text = self.transliterate_text(
                                    comment_text, language, check_ascii=False
                                )
                                if transliterated_text and transliterated_text != comment_text:
                                    # Обновляем текст комментария, сохраняя все остальные атрибуты
                                    tag.text = [transliterated_text]
                                    tags_modified = True
                                    print(f"    Обновлен комментарий: {comment_text[:50]}... -> {transliterated_text[:50]}...")
                except Exception as e:
                    print(f"  Ошибка при обработке комментария {tag_name}: {e}")
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
                                transliterated_text = self.transliterate_text(
                                    txxx_text, language, check_ascii=False
                                )
                                if transliterated_text and transliterated_text != txxx_text:
                                    # Обновляем текст тега, сохраняя описание и кодировку
                                    tag.text = [transliterated_text]
                                    tags_modified = True
                                    desc = tag.desc if hasattr(tag, 'desc') else ''
                                    print(f"    Обновлен пользовательский тег '{desc}': {txxx_text[:50]}... -> {transliterated_text[:50]}...")
                except Exception as e:
                    print(f"  Ошибка при обработке пользовательского тега {tag_name}: {e}")
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
                                transliterated_text = self.transliterate_text(
                                    uslt_text, language, check_ascii=False
                                )
                                if transliterated_text and transliterated_text != uslt_text:
                                    # Обновляем текст песни
                                    tag.text = transliterated_text
                                    tags_modified = True
                                    print(f"    Обновлен текст песни: {len(uslt_text)} символов -> {len(transliterated_text)} символов")
                except Exception as e:
                    print(f"  Ошибка при обработке текста песни {tag_name}: {e}")
                    continue
            
            # Сохраняем изменения, если они были
            if tags_modified:
                try:
                    audio.save()
                    print(f"  ✓ ID3-теги файла '{file_path.name}' транслитерированы и сохранены")
                    return True
                except Exception as e:
                    print(f"  ✗ Ошибка при сохранении тегов: {e}")
                    return False
            else:
                print(f"  - ID3-теги файла '{file_path.name}' не требуют изменений")
                return True
                
        except (ID3NoHeaderError, MutagenError) as e:
            print(f"  ! Ошибка при чтении ID3-тегов файла '{file_path.name}': {e}")
            return False
        except Exception as e:
            print(f"  ! Неожиданная ошибка при обработке ID3-тегов файла '{file_path.name}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_directory(self, directory_path: str):
        """Обрабатывает все файлы в указанной директории"""
        path = Path(directory_path)
        
        if not path.exists():
            print(f"Ошибка: путь '{directory_path}' не существует")
            return False
        
        if not path.is_dir():
            print(f"Ошибка: '{directory_path}' не является директорией")
            return False
        
        # Собираем все файлы в директории
        files = [f for f in path.iterdir() if f.is_file()]
        
        if not files:
            print(f"Директория '{directory_path}' не содержит файлов")
            return True
        
        print(f"Найдено {len(files)} файлов для обработки\n")
        
        # Сначала проверяем все файлы на наличие проблем
        processed_files = {}
        
        for file_path in files:
            original_name = file_path.name
            print(f"Обработка файла: {original_name}")
            
            result = self.process_filename(original_name)
            
            if result[0] is None:
                print(f"  ✗ Ошибка при обработке имени файла\n")
                return False
            
            new_name, language = result
            
            print(f"  Определен язык: {language if language else 'не определен'}")
            print(f"  Новое имя: {new_name}")
            
            # Проверяем на конфликт имен в пределах текущей обработки
            if new_name in [name for name, _, _ in processed_files.values()]:
                print(f"  ✗ Ошибка: конфликт имен при переименовании:")
                print(f"  Файл '{original_name}' должен быть переименован в '{new_name}'")
                print(f"  Но файл с таким именем уже будет создан из другого исходного файла\n")
                return False
            
            # Проверяем, существует ли уже файл с таким именем
            new_path = file_path.parent / new_name
            if new_path.exists() and new_path != file_path:
                print(f"  ✗ Ошибка: файл '{new_name}' уже существует в директории")
                print(f"  Не удалось переименовать '{original_name}'\n")
                return False
            
            processed_files[original_name] = (new_name, language, file_path)
            print(f"  ✓ Файл готов к переименованию\n")
        
        # Если все проверки пройдены, выполняем переименование
        print("=" * 50)
        print("Начинаю переименование файлов...")
        
        for original_name, (new_name, language, file_path) in processed_files.items():
            old_path = file_path
            new_path = old_path.parent / new_name
            
            if old_path != new_path:
                try:
                    old_path.rename(new_path)
                    print(f"✓ Переименован: '{original_name}' -> '{new_name}'")
                except Exception as e:
                    print(f"✗ Ошибка при переименовании '{original_name}': {e}")
                    return False
            else:
                print(f"- Файл '{original_name}' не требует переименования")
            
            # Если файл MP3, транслитерируем ID3-теги
            if new_path.suffix.lower() == '.mp3':
                print(f"  Обработка ID3-тегов MP3-файла...")
                self.transliterate_mp3_tags(new_path, language)
                print()
            else:
                print()
        
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
    
    # Регулярное выражение для поиска существующего префикса
    prefix_pattern = re.compile(r'^\d{4}\s')
    
    # Обрабатываем файлы в каталоге
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        # Пропускаем подкаталоги, обрабатываем только файлы
        if not os.path.isfile(filepath):
            continue
        
        # Удаляем существующий префикс, если он есть
        new_name = filename
        if prefix_pattern.match(filename):
            # Удаляем первые 5 символов (4 цифры + пробел)
            new_name = filename[5:]
        
        # Генерируем новый случайный префикс
        random_number = random.randint(min_value, max_value)
        prefix = f"{random_number:04d} "
        
        # Формируем новое имя файла
        final_name = prefix + new_name
        
        # Переименовываем файл
        new_filepath = os.path.join(directory, final_name)
        try:
            os.rename(filepath, new_filepath)
            print(f"Переименован: {filename} -> {final_name}")
        except Exception as e:
            print(f"Ошибка при переименовании {filename}: {e}")



def main():
    """Основная функция программы"""
    if len(sys.argv) != 2:
        print("Использование: python transliterate_files.py <путь_к_директории>")
        sys.exit(1)
     
    directory_path = sys.argv[1]
    
    if not directory_path:
        print("Ошибка: путь не может быть пустым")
        sys.exit(1)
    
    transliterator = FileTransliterator()
    
    try:
        success = transliterator.process_directory(directory_path)
        if success:
            print("\n" + "=" * 50)
            print("Обработка завершена успешно!")
        else:
            print("\n" + "=" * 50)
            print("Обработка прервана из-за ошибок")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nОбработка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nПроизошла непредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

