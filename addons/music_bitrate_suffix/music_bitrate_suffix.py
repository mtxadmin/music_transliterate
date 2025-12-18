import os
import sys
import re
import platform
from mutagen.mp3 import MP3
from mutagen.mp3 import HeaderNotFoundError
from pathlib import Path

# ANSI escape codes for colors
COLORS = {
    'YELLOW': '\033[33;1m',    # Ярко-желтый для переименований (33 - желтый, 1 - яркий)
    'BRIGHT_RED': '\033[91m',  # Ярко-красный для ошибок
    'BLUE': '\033[94m',        # Ярко-синий
    'GREEN': '\033[92m',       # Ярко-зеленый
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
}

def clear_screen():
    """Безопасная очистка экрана, работающая во всех средах"""
    try:
        # Проверяем, подключен ли вывод к реальному терминалу (tty)
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            system_name = platform.system()
            
            if system_name == "Windows":
                # Для Windows пробуем несколько способов
                try:
                    # Способ 1: ANSI escape code (работает в современных терминалах Windows)
                    sys.stdout.write('\033[2J\033[H')
                    sys.stdout.flush()
                except:
                    # Способ 2: Команда cls через os.system
                    os.system('cls')
            else:
                # Для Linux/Mac используем ANSI escape code
                sys.stdout.write('\033[2J\033[H')
                sys.stdout.flush()
        else:
            # Если не терминал (например, консоль Python), используем альтернативный метод
            # Выводим 50 пустых строк, чтобы сдвинуть старый текст
            print('\n' * 50)
    except:
        # В крайнем случае, просто выводим разделительную линию
        print("\n" + "="*80 + "\n")

def print_color(text, color='RESET', bold=False):
    """Print colored text"""
    color_code = COLORS.get(color.upper(), COLORS['RESET'])
    bold_code = COLORS['BOLD'] if bold else ''
    reset_code = COLORS['RESET']
    print(f"{bold_code}{color_code}{text}{reset_code}")

def show_help():
    """Показать справку по использованию программы"""
    print_color("Программа для поиска и обработки MP3 файлов", "BOLD", bold=True)
    print()
    print("Использование:")
    print_color("  python music_bitrate_suffix.py <путь_к_каталогу>", "BLUE")
    print()
    print("Описание:")
    print("  Программа рекурсивно ищет все MP3 файлы в указанном каталоге,")
    print("  определяет их битрейт и при необходимости переименовывает:")
    print()
    print("  - Если битрейт 320 или 319 kbps, удаляет суффиксы 320 или 319 из имени файла (если они есть)")
    print("  - Если битрейт не 320 или 319 kbps, добавляет его значение в конец имени файла")
    print("  - Убирает пробелы и подчеркивания в конце имени файла")
    print("  - Не добавляет битрейт, если он уже указан в конце имени")
    print()
    print("Примеры:")
    print_color("  python music_bitrate_suffix.py /home/user/Music", "BLUE")
    print_color("  python music_bitrate_suffix.py \"C:\\My Music\"", "BLUE")
    print_color("  python music_bitrate_suffix.py .", "BLUE")
    print()
    print_color("Для работы программы требуется библиотека mutagen:", "BOLD", bold=True)
    print_color("  pip install mutagen", "GREEN")
    print()

def normalize_mp3_extensions(directory):
    """Переименовать все файлы с расширением .MP3 в .mp3"""
    converted_count = 0
    # Используем set для отслеживания уже обработанных файлов
    processed_files = set()
    
    # Собираем все файлы с разными вариантами регистра расширений
    all_mp3_files = []
    
    # Сначала собираем все файлы с разными расширениями
    for pattern in ["*.MP3", "*.Mp3", "*.mP3"]:
        for mp3_file in directory.rglob(pattern):
            # Используем реальный путь файла для избежания дубликатов
            real_path = mp3_file.resolve()
            if real_path not in processed_files:
                processed_files.add(real_path)
                all_mp3_files.append(mp3_file)
    
    # Теперь обрабатываем каждый уникальный файл
    for mp3_file in all_mp3_files:
        try:
            old_path = mp3_file
            new_path = mp3_file.with_suffix('.mp3')
            
            # Проверяем, что новый путь отличается от старого
            if old_path == new_path:
                continue
                
            # Переименовываем только если новый файл не существует
            if not new_path.exists():
                old_path.rename(new_path)
                converted_count += 1
            else:
                print_color(f"Файл {new_path.name} уже существует, пропускаем: {mp3_file.name}", "BRIGHT_RED")
        except Exception as e:
            print_color(f"Ошибка при переименовании {mp3_file.name}: {e}", "BRIGHT_RED")
    
    return converted_count

def get_mp3_bitrate(file_path):
    """Получить битрейт MP3 файла"""
    try:
        audio = MP3(file_path)
        
        # Проверяем, что файл действительно MP3
        if not audio or not audio.info:
            return None, "Не удалось прочитать информацию о файле"
        
        # Библиотека mutagen возвращает битрейт в bps, переводим в kbps
        bitrate_kbps = audio.info.bitrate // 1000
        
        # Проверяем, что битрейт в разумных пределах
        if bitrate_kbps < 32 or bitrate_kbps > 320:
            return None, f"Неверный битрейт {bitrate_kbps} kbps"
        
        return bitrate_kbps, ""
        
    except FileNotFoundError:
        return None, "Файл не найден"
    except PermissionError:
        return None, "Нет доступа к файлу"
    except HeaderNotFoundError:
        return None, "Файл не является корректным MP3"
    except Exception as e:
        return None, f"Ошибка чтения: {type(e).__name__}"

def clean_trailing_chars(filename):
    """Убрать пробелы и подчеркивания в конце имени файла (без расширения)"""
    # Разделяем имя и расширение
    name, ext = os.path.splitext(filename)
    
    # Убираем пробелы и подчеркивания с конца
    cleaned_name = name.rstrip(' _')
    
    return cleaned_name, ext

def should_add_bitrate(filename, bitrate_kbps):
    """Проверить, нужно ли добавлять битрейт к имени файла"""
    # Убираем расширение
    name, _ = os.path.splitext(filename)
    
    # Убираем пробелы и подчеркивания с конца
    cleaned_name = name.rstrip(' _')
    
    # Ищем число в конце имени
    match = re.search(r'(\d+)$', cleaned_name)
    
    if match:
        existing_number = int(match.group(1))
        # Если число в конце совпадает с битрейтом, не добавляем
        if existing_number == bitrate_kbps:
            return False, cleaned_name
        else:
            return True, cleaned_name
    else:
        # Если числа нет, нужно добавить (если битрейт не 320 и не 319)
        return bitrate_kbps not in (320, 319), cleaned_name

def remove_320_suffix(filename, bitrate_kbps):
    """Удалить суффикс 319 или 320 из имени файла, если битрейт 319 или 320"""
    # Разделяем имя и расширение
    name, ext = os.path.splitext(filename)
    
    # Убираем пробелы и подчеркивания с конца
    cleaned_name = name.rstrip(' _')
    
    # Проверяем, заканчивается ли имя на число 319 или 320
    match = re.search(r'(\d+)$', cleaned_name)
    
    if match:
        existing_number = int(match.group(1))
        # Если битрейт 319 или 320 И найденное число тоже 319 или 320, то удаляем
        # Теперь удаляем независимо от совпадения: если битрейт 319 или 320, и в конце 319 или 320
        if bitrate_kbps in (319, 320) and existing_number in (319, 320):
            # Удаляем число и пробелы/подчеркивания перед ним
            # Ищем все пробелы и подчеркивания перед числом
            base_name = cleaned_name[:match.start()]
            # Убираем оставшиеся пробелы и подчеркивания с конца
            base_name = base_name.rstrip(' _')
            # Возвращаем новое имя
            return base_name + ext
    
    # Если не нашли суффикс для удаления, возвращаем исходное имя
    return filename

def process_mp3_file(file_path):
    """Обработать один MP3 файл"""
    # Получаем битрейт файла
    bitrate_kbps, error_message = get_mp3_bitrate(file_path)
    if bitrate_kbps is None:
        # Выводим сообщение об ошибке чтения файла
        filename = os.path.basename(file_path)
        print_color(f"{error_message}: {filename}", "BRIGHT_RED")
        return False, False  # (успех, переименован с битрейтом)
    
    # Получаем имя файла и путь к директории
    dir_name = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    
    # Если битрейт 319 или 320, проверяем, нужно ли удалить суффикс
    if bitrate_kbps in (319, 320):
        # Пытаемся удалить суффикс 319/320 (теперь удаляем независимо от совпадения)
        new_name = remove_320_suffix(filename, bitrate_kbps)
        
        # Если имя изменилось, переименовываем файл
        if new_name != filename:
            new_path = os.path.join(dir_name, new_name)
            try:
                os.rename(file_path, new_path)
                # Определяем, какой суффикс был удален
                old_name_without_ext = os.path.splitext(filename)[0].rstrip(' _')
                match = re.search(r'(\d+)$', old_name_without_ext)
                if match:
                    removed_suffix = match.group(1)
                    print_color(f"Удален суффикс {removed_suffix}: {filename} -> {new_name} (битрейт: {bitrate_kbps} kbps)", "YELLOW")
                else:
                    print_color(f"Удален суффикс: {filename} -> {new_name} (битрейт: {bitrate_kbps} kbps)", "YELLOW")
                return True, False  # (успех, не переименован с добавлением битрейта, но изменен)
            except Exception as e:
                print_color(f"Ошибка при переименовании {filename}: {e}", "BRIGHT_RED")
                return False, False
    
    # Проверяем, нужно ли добавлять битрейт (для оставшихся файлов или если суффикс не удалялся)
    need_to_add, cleaned_name = should_add_bitrate(filename, bitrate_kbps)
    
    # Изменено условие: теперь проверяем, что битрейт не 320 и не 319
    if need_to_add and bitrate_kbps not in (320, 319):
        # Убираем расширение и очищаем от пробелов/подчеркиваний в конце
        name_without_ext, ext = clean_trailing_chars(filename)
        
        # Формируем новое имя файла
        new_name = f"{name_without_ext} {bitrate_kbps}{ext}"
        new_path = os.path.join(dir_name, new_name)
        
        # Проверяем, что новый путь отличается от старого
        if new_path == file_path:
            print(f"Файл {filename} не требует изменений (битрейт: {bitrate_kbps} kbps)")
            return True, False  # (успех, переименован с битрейтом)
        
        # Безопасно переименовываем файл
        try:
            os.rename(file_path, new_path)
            print_color(f"Переименован: {filename} -> {new_name} (битрейт: {bitrate_kbps} kbps)", "YELLOW")
            return True, True  # (успех, переименован с битрейтом)
        except Exception as e:
            print_color(f"Ошибка при переименовании {filename}: {e}", "BRIGHT_RED")
            return False, False
    else:
        # Если не нужно добавлять битрейт (битрейт 319 или 320), но нужно очистить имя
        name_without_ext, ext = clean_trailing_chars(filename)
        if name_without_ext + ext != filename:
            new_path = os.path.join(dir_name, name_without_ext + ext)
            try:
                os.rename(file_path, new_path)
                print(f"Очищено имя: {filename} -> {name_without_ext + ext}")
                return True, False  # (успех, переименован с битрейтом)
            except Exception as e:
                print_color(f"Ошибка при переименовании {filename}: {e}", "BRIGHT_RED")
                return False, False
        else:
            print(f"Файл {filename} не требует изменений (битрейт: {bitrate_kbps} kbps)")
            return True, False  # (успех, переименован с битрейтом)

def find_and_process_mp3_files(directory):
    """Рекурсивно найти и обработать все MP3 файлы в директории"""
    directory = Path(directory)
    
    if not directory.exists():
        print_color(f"Ошибка: Директория '{directory}' не существует!", "BRIGHT_RED", bold=True)
        sys.exit(1)
    
    if not directory.is_dir():
        print_color(f"Ошибка: '{directory}' не является директорией!", "BRIGHT_RED", bold=True)
        sys.exit(1)
    
    # Сначала нормализуем расширения всех MP3 файлов
    converted = normalize_mp3_extensions(directory)
    
    # Выводим информацию о нормализации только если были переименованы файлы
    if converted > 0:
        print_color("Нормализация расширений MP3 файлов...", "BLUE", bold=True)
        print("-" * 60)
        print(f"Нормализовано расширений: {converted} файлов")
        print("-" * 60)
    
    # Теперь ищем только файлы с расширением .mp3
    mp3_files = list(directory.rglob("*.mp3"))
    
    if not mp3_files:
        print("MP3 файлы не найдены")
        return
    
    print_color(f"Найдено {len(mp3_files)} MP3 файлов в директории '{directory}'", "GREEN", bold=True)
    print("-" * 60)
    
    # Статистика обработки
    processed = 0
    renamed_with_bitrate = 0  # Количество переименований с добавлением битрейта
    errors = 0
    
    # Обрабатываем каждый файл
    for mp3_file in mp3_files:
        file_path = str(mp3_file)
        try:
            success, renamed = process_mp3_file(file_path)
            if success:
                processed += 1
                if renamed:
                    renamed_with_bitrate += 1
            else:
                errors += 1
        except KeyboardInterrupt:
            print_color("\nПрервано пользователем", "BRIGHT_RED", bold=True)
            sys.exit(1)
        except Exception as e:
            print_color(f"Необработанная ошибка для файла {file_path}: {e}", "BRIGHT_RED", bold=True)
            errors += 1
    
    print("-" * 60)
    print_color(f"Обработка завершена!", "GREEN", bold=True)
    print(f"Успешно обработано файлов: {processed}")
    print(f"Из них переименовано с добавлением битрейта: {renamed_with_bitrate}")
    print(f"Ошибок: {errors}")

def main():
    """Основная функция программы"""
    # Безопасно очищаем экран (только если вывод в реальный терминал)
    clear_screen()
    
    # Добавляем информационный заголовок
    print_color("=" * 60, "GREEN", bold=True)
    print_color("MP3 Bitrate Renamer Tool", "GREEN", bold=True)
    print_color("=" * 60, "GREEN", bold=True)
    print()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) != 2:
        show_help()
        sys.exit(1)
    
    # Получаем путь к директории из аргументов
    directory = sys.argv[1].strip()
    
    # Проверяем, не пустой ли путь
    if not directory:
        print_color("Ошибка: Путь к каталогу не указан!", "BRIGHT_RED", bold=True)
        show_help()
        sys.exit(1)
    
    # Обрабатываем MP3 файлы
    find_and_process_mp3_files(directory)

if __name__ == "__main__":
    # Проверяем наличие необходимой библиотеки
    try:
        from mutagen.mp3 import MP3, HeaderNotFoundError
        main()
    except ImportError:
        clear_screen()
        print_color("Ошибка: Необходимо установить библиотеку mutagen", "BRIGHT_RED", bold=True)
        print_color("Установите с помощью:", "BRIGHT_RED")
        print_color("  pip install mutagen", "GREEN")
        sys.exit(1)
