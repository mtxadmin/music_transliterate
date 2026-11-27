# https://github.com/mtxadmin/music_transliterate/
# Many thanks to Deepseek AI, who greatly helped with writing and debugging of this script


# Файловые операции: числовые префиксы, копирование в output-dir, обработка одной папки и пакета папок, путь к конфигу.


import os
import re
import sys
import random
import shutil
import threading
import traceback
from pathlib import Path
from typing import Optional, Tuple, Set, List, Callable


# Движок транслитерации (часть 2 из 4).
from music_transliterate_core import (
    FileTransliterator,
    safe_stderr_write,
    safe_stdout_write,
)


def add_number_prefixes(directory: str, flag_ge_1000: bool = False,
                        cancel_event: Optional[threading.Event] = None,
                        files: Optional[List[str]] = None,
                        progress_callback: Optional[Callable[[int, int], None]] = None,
                        recursive: bool = False) -> None:
    """
    Добавляет к именам файлов случайные числовые префиксы.

    files: если задан, обрабатываются только перечисленные имена (в directory).
           Если None — все файлы в directory (или рекурсивно при recursive=True).
    """
    
    # Проверяем существование каталога
    if not os.path.isdir(directory):
        raise ValueError(f"Каталог '{directory}' не существует")
    
    # Определяем диапазон случайных чисел
    min_value = 1000 if flag_ge_1000 else 1
    max_value = 9999
    
    # Регулярное выражение для поиска существующего префикса (4 цифры + пробел в начале)
    prefix_pattern = re.compile(r'^\d{4}\s')

    if files is not None:
        file_paths = [Path(directory) / (Path(f).name if isinstance(f, Path) else f) for f in files]
        file_paths = [f for f in file_paths if f.is_file()]
    else:
        root = Path(directory)
        if recursive:
            file_paths = [f for f in root.rglob('*') if f.is_file()]
        else:
            file_paths = [f for f in root.iterdir() if f.is_file()]

    if not file_paths:
        safe_stdout_write(f"Каталог '{directory}' не содержит файлов\n")
        return

    safe_stdout_write(f"\n" + "=" * 50 + "\n")
    safe_stdout_write(f"Добавление числовых префиксов...\n")
    safe_stdout_write(f"Файлов: {len(file_paths)}\n")
    safe_stdout_write(f"Диапазон префиксов: {min_value:04d}-{max_value:04d}\n\n")

    total = len(file_paths)

    for idx, file_path in enumerate(file_paths):
        if cancel_event and cancel_event.is_set():
            safe_stdout_write("Добавление префиксов отменено пользователем\n")
            return
        if progress_callback:
            try:
                progress_callback(idx + 1, total)
            except Exception:
                pass

        parent = file_path.parent
        filename = file_path.name

        new_name = filename
        # Удаляем существующий префикс, если он есть
        if prefix_pattern.match(filename):
            # Удаляем первые 5 символов (4 цифры + пробел)
            new_name = filename[5:]
            safe_stdout_write(f"  Удален существующий префикс у файла: {file_path}\n")

        max_tries = 100
        final_name = None
        final_filepath = None
        for _ in range(max_tries):
            # Генерируем случайный префикс
            random_number = random.randint(min_value, max_value)
            prefix = f"{random_number:04d} "

            # Формируем новое имя файла
            candidate_name = prefix + new_name
            candidate_path = parent / candidate_name
            if candidate_path == file_path:
                continue
            if not candidate_path.exists():
                final_name = candidate_name
                final_filepath = candidate_path
                break

        if final_name is None:
            safe_stderr_write(f"✗ Не удалось подобрать уникальный префикс для {file_path}\n")
            continue

        try:
            file_path.rename(final_filepath)
            safe_stdout_write(f"✓ Добавлен префикс: {file_path} -> {final_name}\n")
        except Exception as e:
            safe_stderr_write(f"✗ Ошибка при переименовании {file_path}: {e}\n")


def _preview_prefixes(path: str, ge_1000: bool = False,
                      cancel_event: Optional[threading.Event] = None,
                      names: Optional[List[str]] = None,
                      recursive: bool = False) -> None:
    """Показывает, какие файлы получат префиксы (без реального переименования).

    names: если задан, используются эти имена. Если None, берутся файлы из path.
    """
    if names is None:
        p = Path(path)
        if not p.is_dir():
            return
        if recursive:
            files = [f for f in p.rglob('*') if f.is_file()]
            names = [str(f.relative_to(p)) for f in files]
        else:
            files = [f for f in p.iterdir() if f.is_file()]
            names = [f.name for f in files]
    if not names:
        safe_stdout_write("Файлов нет\n")
        return
    min_val = 1000 if ge_1000 else 1
    prefix_pattern = re.compile(r'^\d{4}\s')
    safe_stdout_write(f"Файлов будет обработано: {len(names)}\n")
    safe_stdout_write(f"Диапазон префиксов: {min_val:04d}-9999\n")
    for name in names:
        if cancel_event and cancel_event.is_set():
            safe_stdout_write("Отменено\n")
            return
        base = Path(name).name
        cleaned = prefix_pattern.sub('', base) if prefix_pattern.match(base) else base
        parent = str(Path(name).parent)
        prefix_path = (parent + os.sep) if parent and parent != '.' else ''
        safe_stdout_write(f"  Получит префикс: '{name}' -> '{prefix_path}[XXXX] {cleaned}'\n")


def _copy_files_to_output(source_dir: str, output_dir: str, used_names: Set[str],
                          testonly: bool,
                          transliterate_id3: bool = False,
                          recursive: bool = False,
                          cancel_event: Optional[threading.Event] = None,
                          progress_callback: Optional[Callable[[int, int], None]] = None
                          ) -> Tuple[bool, List[Tuple[Path, Path]]]:
    """Копирует все файлы из source_dir в output_dir с исходными именами (с дедупликацией).
    Опционально транслитерирует ID3-теги у mp3. При recursive=True — из вложенных папок тоже.
    Возвращает (success, [(source_path, target_path), ...])."""
    src = Path(source_dir)
    out = Path(output_dir)

    if not src.exists() or not src.is_dir():
        safe_stderr_write(f"Ошибка: путь '{source_dir}' не существует или не директория\n")
        return False, []

    if recursive:
        files = [f for f in src.rglob('*') if f.is_file()]
    else:
        files = [f for f in src.iterdir() if f.is_file()]

    if not files:
        safe_stdout_write(f"Директория '{source_dir}' не содержит файлов\n")
        return True, []

    if not testonly:
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            safe_stderr_write(f"Ошибка создания папки результата '{output_dir}': {e}\n")
            return False, []

    tr_instance = FileTransliterator(cancel_event=cancel_event) if transliterate_id3 else None

    safe_stdout_write(f"Найдено {len(files)} файлов для копирования\n\n")

    results: List[Tuple[Path, Path]] = []
    for idx, f in enumerate(files):
        if cancel_event and cancel_event.is_set():
            safe_stdout_write("Копирование отменено пользователем\n")
            return False, results
        if progress_callback:
            try:
                progress_callback(idx + 1, len(files))
            except Exception:
                pass

        name = f.name

        def is_taken(n: str) -> bool:
            if n in used_names:
                return True
            if (out / n).exists():
                return True
            return False

        if is_taken(name):
            stem, ext = os.path.splitext(name)
            counter = 1
            while True:
                candidate = f"{stem} ({counter}){ext}"
                if not is_taken(candidate):
                    name = candidate
                    break
                counter += 1
            safe_stdout_write(f"  Имя скорректировано, чтобы избежать конфликта: {name}\n")

        used_names.add(name)
        target = out / name

        if testonly:
            safe_stdout_write(f"  [ТЕСТ] Копирование: '{f}' -> '{target}'\n")
            if transliterate_id3 and f.suffix.lower() == '.mp3':
                safe_stdout_write(f"    Транслитерация ID3-тегов MP3\n")
        else:
            try:
                shutil.copy2(f, target)
                safe_stdout_write(f"✓ Скопирован: '{f.name}' -> '{name}'\n")
            except Exception as e:
                safe_stderr_write(f"✗ Ошибка копирования {f.name}: {e}\n")
                continue

            if transliterate_id3 and target.suffix.lower() == '.mp3' and tr_instance is not None:
                safe_stdout_write(f"  Обработка ID3-тегов MP3-файла...\n")
                tr_instance.transliterate_mp3_tags(target, None)
                safe_stdout_write("\n")

        results.append((f, target))

    return True, results


def run_operation_output(path: str, output_dir: str, ge_1000: bool,
                         add_prefixes: bool, transliterate_names: bool,
                         transliterate_id3: bool,
                         testonly: bool, used_names: Set[str],
                         recursive: bool = False,
                         cancel_event: Optional[threading.Event] = None,
                         progress_callback: Optional[Callable[[int, int], None]] = None) -> None:
    """Копирование в output_dir с трансформациями (без изменения исходников)."""
    if not add_prefixes and not transliterate_names and not transliterate_id3:
        safe_stdout_write("ВНИМАНИЕ: все операции отключены — файлы будут просто скопированы.\n")

    if transliterate_names:
        tr = FileTransliterator(cancel_event=cancel_event)
        success, results = tr.process_directory(
            path, testonly=testonly,
            process_id3=transliterate_id3,
            output_dir=output_dir, used_names=used_names,
            transliterate_names=True,
            recursive=recursive,
            progress_callback=progress_callback
        )
        if not success:
            raise RuntimeError('Обработка прервана из-за ошибок')
    else:
        success, results = _copy_files_to_output(
            path, output_dir, used_names, testonly,
            transliterate_id3=transliterate_id3,
            recursive=recursive,
            cancel_event=cancel_event,
            progress_callback=progress_callback
        )
        if not success:
            raise RuntimeError('Копирование прервано из-за ошибок')

    if cancel_event and cancel_event.is_set():
        return

    if add_prefixes:
        target_names = [tgt.name for _, tgt in results]
        if testonly:
            _preview_prefixes(path, ge_1000, cancel_event, names=target_names)
        else:
            safe_stdout_write("\n" + "=" * 50 + "\n")
            safe_stdout_write("ШАГ 2: ДОБАВЛЕНИЕ ЧИСЛОВЫХ ПРЕФИКСОВ\n")
            safe_stdout_write("=" * 50 + "\n")
            add_number_prefixes(output_dir, ge_1000, cancel_event, files=target_names)


def run_operation(path: str, ge_1000: bool = False, add_prefixes: bool = False,
                  transliterate_names: bool = False, transliterate_id3: bool = False,
                  testonly: bool = False, output_dir: Optional[str] = None,
                  used_names: Optional[Set[str]] = None,
                  recursive: bool = False,
                  cancel_event: Optional[threading.Event] = None,
                  progress_callback: Optional[Callable[[int, int], None]] = None) -> None:
    """Единая точка входа. Бросает RuntimeError при ошибке.

    output_dir=None  -> старое поведение (переименование на месте).
    output_dir=<путь> -> копирование в папку результата, исходники не трогаются.
    used_names — общий set для дедупликации между папками (только для output_dir).
    """
    if output_dir is not None:
        if used_names is None:
            used_names = set()
        run_operation_output(path, output_dir, ge_1000, add_prefixes,
                             transliterate_names, transliterate_id3,
                             testonly, used_names, recursive,
                             cancel_event, progress_callback)
        return

    # In-place режим
    results: List[Tuple[Path, Path]] = []
    if transliterate_names or transliterate_id3:
        tr = FileTransliterator(cancel_event=cancel_event)
        success, results = tr.process_directory(
            path, testonly=testonly,
            process_id3=transliterate_id3,
            transliterate_names=transliterate_names,
            recursive=recursive,
            progress_callback=progress_callback
        )
        if not success:
            raise RuntimeError('Обработка прервана из-за ошибок')

    if cancel_event and cancel_event.is_set():
        return

    if add_prefixes:
        if testonly:
            _preview_prefixes(path, ge_1000, cancel_event, recursive=recursive)
        else:
            safe_stdout_write("\n" + "=" * 50 + "\n")
            safe_stdout_write("ШАГ 2: ДОБАВЛЕНИЕ ЧИСЛОВЫХ ПРЕФИКСОВ\n")
            safe_stdout_write("=" * 50 + "\n")
            add_number_prefixes(path, ge_1000, cancel_event,
                                progress_callback=progress_callback,
                                recursive=recursive)


def run_batch(folders: List[dict], output_dir: Optional[str], testonly: bool,
              add_prefixes: bool = True, transliterate_names: bool = True,
              transliterate_id3: bool = True,
              cancel_event: Optional[threading.Event] = None,
              progress_callback: Optional[Callable[[int, int], None]] = None,
              folder_progress_callback: Optional[Callable[[int, int, str], None]] = None
              ) -> dict:
    """Обрабатывает несколько папок последовательно в общую output_dir.

    folders: список dict с ключами path, ge_1000, recursive.
    В тестовом режиме (testonly=True) проверка прерывается на первой ошибке,
    в боевом — ошибки собираются, а обработка продолжается.
    Возвращает {'success': [path, ...], 'failed': [(path, err), ...]}.
    """
    used_names: Set[str] = set()
    total = len(folders)
    success_list: List[str] = []
    failed_list: List[Tuple[str, str]] = []
    aborted = False

    for i, fc in enumerate(folders):
        if cancel_event and cancel_event.is_set():
            safe_stdout_write("\nОбработка отменена пользователем\n")
            break

        if folder_progress_callback:
            try:
                folder_progress_callback(i, total, fc.get('path', ''))
            except Exception:
                pass

        try:
            run_operation(
                fc['path'],
                output_dir=output_dir if output_dir else None,
                ge_1000=fc.get('ge_1000', False),
                add_prefixes=add_prefixes,
                transliterate_names=transliterate_names,
                transliterate_id3=transliterate_id3,
                testonly=testonly,
                used_names=used_names,
                recursive=fc.get('recursive', False),
                cancel_event=cancel_event,
                progress_callback=progress_callback,
            )
            success_list.append(fc['path'])
        except RuntimeError as e:
            safe_stderr_write(f"✗ Ошибка при обработке '{fc.get('path', '')}': {e}\n")
            failed_list.append((fc.get('path', ''), str(e)))
            if testonly:
                aborted = True
                break
        except Exception as e:
            safe_stderr_write(f"✗ Неожиданная ошибка при обработке '{fc.get('path', '')}': {e}\n")
            traceback.print_exc(file=sys.stderr)
            failed_list.append((fc.get('path', ''), str(e)))
            if testonly:
                aborted = True
                break

    if folder_progress_callback:
        try:
            folder_progress_callback(total, total,
                                     'Прервано' if aborted else 'Готово')
        except Exception:
            pass

    safe_stdout_write("\n" + "=" * 70 + "\n")
    if aborted:
        safe_stdout_write("Тестирование прервано на первой ошибке\n")
    safe_stdout_write(f"ИТОГО: успешно {len(success_list)}, с ошибками {len(failed_list)}\n")
    if aborted:
        not_checked = total - len(success_list) - len(failed_list)
        if not_checked > 0:
            safe_stdout_write(f"Не проверено папок: {not_checked}\n")
    if failed_list:
        safe_stdout_write("Папки с ошибками:\n")
        for p, err in failed_list:
            safe_stdout_write(f"  - {p}: {err}\n")
    safe_stdout_write("=" * 70 + "\n")

    return {'success': success_list, 'failed': failed_list}


# ====================== Конфиг ======================

def get_config_path() -> Path:
    """Определяет путь к конфигу. Рядом со скриптом; если read-only — %APPDATA% или домашняя папка."""
    script_dir = Path(__file__).resolve().parent
    config_file = script_dir / 'music_transliterate.config'
    try:
        test_file = script_dir / f'.write_test_{os.getpid()}'
        test_file.touch()
        test_file.unlink()
        return config_file
    except (OSError, PermissionError):
        pass

    appdata = os.environ.get('APPDATA')
    if appdata:
        return Path(appdata) / 'music_transliterate.config'
    return Path.home() / 'music_transliterate.config'
