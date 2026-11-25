# https://github.com/mtxadmin/music_transliterate/
# Many thanks to Deepseek AI, who greatly helped with writing and debugging of this script


# Точка входа: GUI (tkinter) и CLI.


# модуль transliterate - херня, детектит всё как ru. Issue сделал, но проект старый и заброшенный
# https://github.com/barseghyanartur/transliterate/issues/73
# также, этот модуль транслитерирует криво. й в j, например. Короче, лучше без него


# GUI-оболочка: tkinter (в стандартной поставке Python)
# Конфиг: PyYAML. Установка: pip install mutagen pyyaml


import sys
import threading
import queue
import traceback
import contextlib
import datetime
import webbrowser
from pathlib import Path
from typing import Any, Tuple, Optional, List

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    HAS_TK = True
except ImportError:
    HAS_TK = False

# Движок
from music_transliterate_core import (
    safe_stderr_write,
    safe_stdout_write,
)

# Файловые операции
from music_transliterate_ops import (
    get_config_path,
    run_batch,
    run_operation,
)


# ====================== GUI ======================

# Цвета для кнопок
COLOR_GREEN = '#28a745'
COLOR_RED = '#dc3545'
COLOR_YELLOW = '#ffc107'
COLOR_GRAY = '#cccccc'
COLOR_GRAY_FG = '#888888'
COLOR_LINK = '#0563c1'

# Ширина кнопки "Тестировать источники" (по наибольшему варианту текста)
TEST_BTN_WIDTH = 23
# Ширина кнопки "Со вложенными" / "Без вложенных" (по наибольшему варианту)
RECURSIVE_BTN_WIDTH = 14


class QueueWriter:
    """Перенаправляет вывод (stdout/stderr) в очередь для чтения главным потоком."""
    def __init__(self, q: queue.Queue, stream_name: str):
        self.q = q
        self.stream_name = stream_name

    def write(self, text: str) -> None:
        if text:
            self.q.put((self.stream_name, text))

    def flush(self) -> None:
        pass


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner_frame = ttk.Frame(self.canvas)

        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.inner_frame.bind("<Configure>", self._update_scrollregion)

        # Глобальный хук на колесо мыши; срабатывает только когда курсор над нашей областью
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._canvas_window, width=event.width)

    def _update_scrollregion(self, event=None):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            _, _, x2, y2 = bbox
            # Верхняя граница scrollregion жёстко = 0 — иначе canvas даёт
            # "прокрутиться выше первого элемента".
            self.canvas.configure(scrollregion=(0, 0, x2, y2))

    def _on_mousewheel(self, event):
        w = event.widget
        while w is not None:
            if w is self.canvas:
                delta = event.delta
                if delta == 0:
                    return
                bbox = self.canvas.bbox("all")
                if not bbox:
                    return
                content_h = bbox[3] - bbox[1]
                visible_h = self.canvas.winfo_height()
                if content_h <= visible_h:
                    return
                # 60px на "щелчок" колеса
                px_step = (-delta / 120.0) * 60.0
                cur_first, _ = self.canvas.yview()
                cur_px = cur_first * content_h
                max_px = content_h - visible_h
                new_px = max(0.0, min(max_px, cur_px + px_step))
                self.canvas.yview_moveto(new_px / content_h)
                return
            w = getattr(w, 'master', None)

    def _on_mousewheel_linux(self, event):
        w = event.widget
        while w is not None:
            if w is self.canvas:
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")
                return
            w = getattr(w, 'master', None)


class FolderRow:
    """Один блок пути: [вложенность] [prefix] [Путь:____] [Обзор] [Убрать]"""

    def __init__(self, parent, gui, config: Optional[dict] = None):
        self.gui = gui
        cfg = config or {}

        self.ge_1000_var = tk.BooleanVar(value=bool(cfg.get('ge_1000', False)))
        self.recursive_var = tk.BooleanVar(value=bool(cfg.get('recursive', False)))

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='x', pady=3, padx=2)

        row = ttk.Frame(self.frame)
        row.pack(fill='x')

        self.recursive_btn = tk.Button(
            row, text=self._recursive_text(), command=self._toggle_recursive,
            font=('Courier New', 8, 'bold'),
            width=RECURSIVE_BTN_WIDTH, padx=2, pady=2,
            bg='#eaeaea', fg='black', relief='raised',
        )
        self.recursive_btn.pack(side='left', padx=(0, 6))

        self.prefix_btn = tk.Button(
            row, text=self._prefix_text(), command=self._toggle_prefix,
            font=('Courier New', 9, 'bold'),
            width=13, padx=2, pady=2,
            bg='#eaeaea', fg='black', relief='raised',
        )
        self.prefix_btn.pack(side='left', padx=(0, 6))

        ttk.Label(row, text='Путь:').pack(side='left')
        self.path_var = tk.StringVar(value=cfg.get('path', ''))
        self.path_entry = ttk.Entry(row, textvariable=self.path_var)
        self.path_entry.pack(side='left', fill='x', expand=True, padx=5)

        self.browse_btn = ttk.Button(row, text='Обзор...', command=self._browse)
        self.browse_btn.pack(side='left', padx=2)
        self.remove_btn = ttk.Button(row, text='Убрать', command=self._remove)
        self.remove_btn.pack(side='left', padx=2)

        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=(3, 0))

        self.update_enabled_state()

    def _prefix_text(self) -> str:
        return '[1000-9999]' if self.ge_1000_var.get() else '[0001-9999]'

    def _recursive_text(self) -> str:
        return 'Со вложенными' if self.recursive_var.get() else 'Без вложенных'

    def _toggle_prefix(self):
        self.ge_1000_var.set(not self.ge_1000_var.get())
        self.prefix_btn.config(text=self._prefix_text())

    def _toggle_recursive(self):
        self.recursive_var.set(not self.recursive_var.get())
        self.recursive_btn.config(text=self._recursive_text())

    def _browse(self):
        current = self.path_var.get().strip()
        initial = current if current and Path(current).is_dir() else None
        try:
            d = filedialog.askdirectory(initialdir=initial) if initial else filedialog.askdirectory()
        except Exception:
            d = filedialog.askdirectory()
        if d:
            self.path_var.set(d)

    def _remove(self):
        self.gui.remove_folder(self)

    def update_enabled_state(self):
        """Включает/выключает кнопку префиксов в зависимости от глобальной настройки.
        Значение ge_1000 всё равно сохраняется в конфиг."""
        if self.gui.add_prefixes_var.get():
            self.prefix_btn.config(state='normal', bg='#eaeaea', fg='black')
        else:
            self.prefix_btn.config(state='disabled', bg=COLOR_GRAY, fg=COLOR_GRAY_FG)

    def to_config(self) -> dict:
        return {
            'path': self.path_var.get().strip(),
            'ge_1000': self.ge_1000_var.get(),
            'recursive': self.recursive_var.get(),
        }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Обработка MP3 для китайских магнитол")
        self.geometry("1050x820")

        self.cancel_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.log_queue: "queue.Queue[Tuple[str, Any]]" = queue.Queue()

        # ============ Верхняя часть: слева папки, справа общие настройки ============
        top = ttk.Frame(self)
        top.pack(fill='both', expand=True, padx=5, pady=(5, 0))

        # Левая колонка
        left = ttk.Frame(top)
        left.pack(side='left', fill='both', expand=True)

        ttk.Label(left, text='Откуда брать файлы:',
                  font=('Arial', 9, 'bold')).pack(anchor='w', padx=2)

        self.scroll = ScrollableFrame(left)
        self.scroll.pack(fill='both', expand=True, pady=(2, 0))

        self.folder_rows: List[FolderRow] = []

        # Кнопка "+ Добавить папку" внутри прокручиваемой области, под последней строкой.
        self.add_btn = ttk.Button(self.scroll.inner_frame, text='+ Добавить папку',
                                  command=self.add_folder)

        # Правая колонка
        right = ttk.LabelFrame(top, text='Общие настройки', padding=10)
        right.pack(side='right', fill='y', padx=(10, 0))

        self.add_prefixes_var = tk.BooleanVar(value=True)
        self.transliterate_names_var = tk.BooleanVar(value=True)
        self.transliterate_id3_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            right, text='Добавлять случайные префиксы',
            variable=self.add_prefixes_var,
            command=self._update_prefix_buttons,
        ).pack(anchor='w', pady=2)

        ttk.Checkbutton(
            right, text='Транслитерация имён файлов',
            variable=self.transliterate_names_var,
        ).pack(anchor='w', pady=2)

        ttk.Checkbutton(
            right, text='Транслитерация ID3-тегов',
            variable=self.transliterate_id3_var,
        ).pack(anchor='w', pady=2)

        # Футер внизу правой колонки — набор меток с переносом (wraplength),
        # ничего не обрезается и не прокручивается.
        footer = ttk.Frame(right)
        footer.pack(side='bottom', fill='x', pady=(20, 0))

        tk.Label(
            footer, text='Сайт проекта:',
            font=('Arial', 8), anchor='w', justify='left',
        ).pack(anchor='w', fill='x')

        proj_link = tk.Label(
            footer, text='github.com/mtxadmin/music_transliterate',
            fg=COLOR_LINK, font=('Arial', 8, 'underline'),
            cursor='hand2', anchor='w', justify='left', wraplength=210,
        )
        proj_link.pack(anchor='w', fill='x')
        proj_link.bind(
            '<Button-1>',
            lambda e: webbrowser.open('https://github.com/mtxadmin/music_transliterate'),
        )

        ttk.Frame(footer, height=10).pack(anchor='w', fill='x')

        tk.Label(
            footer, text='Изменения? Дополнения? Ошибки? Пожелания?',
            font=('Arial', 8), anchor='w', justify='left', wraplength=210,
        ).pack(anchor='w', fill='x')

        fb_frame = ttk.Frame(footer)
        fb_frame.pack(anchor='w', fill='x')
        fb_link = tk.Label(
            fb_frame, text='Пишите сюда',
            fg=COLOR_LINK, font=('Arial', 8, 'underline'),
            cursor='hand2',
        )
        fb_link.pack(side='left')
        fb_link.bind(
            '<Button-1>',
            lambda e: webbrowser.open('https://github.com/mtxadmin/music_transliterate/issues/new'),
        )
        tk.Label(fb_frame, text='.', font=('Arial', 8)).pack(side='left')

        # ============ Папка результата ============
        out_frame = ttk.Frame(self)
        out_frame.pack(fill='x', padx=5, pady=(10, 0))
        ttk.Label(out_frame, text='Куда копировать обработанные файлы:').pack(side='left')
        self.output_var = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.output_var).pack(
            side='left', fill='x', expand=True, padx=5
        )
        ttk.Button(out_frame, text='Обзор...', command=self.browse_output).pack(side='left')

        # ============ Блок кнопок (по центру) ============
        btn_outer = ttk.Frame(self)
        btn_outer.pack(fill='x', padx=5, pady=(10, 0))
        btn_inner = ttk.Frame(btn_outer)
        btn_inner.pack()

        self.test_btn = tk.Button(
            btn_inner, text='Тестировать источники',
            command=self.start_test,
            font=('Arial', 10, 'bold'),
            bg=COLOR_YELLOW, fg='black',
            width=TEST_BTN_WIDTH, padx=10, pady=5, relief='raised',
        )
        self.test_btn.pack(side='left', padx=(0, 10))

        self.start_btn = tk.Button(
            btn_inner, text='Запустить',
            command=self.start,
            font=('Arial', 13, 'bold'),
            bg=COLOR_GREEN, fg='white',
            padx=25, pady=7, relief='raised',
        )
        self.start_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_inner, text='Остановить',
            command=self.stop,
            font=('Arial', 10, 'bold'),
            bg=COLOR_GRAY, fg=COLOR_GRAY_FG,
            padx=15, pady=5, relief='raised',
            state='disabled',
        )
        self.stop_btn.pack(side='left')

        # ============ Прогресс (на всю ширину) ============
        prog_frame = ttk.Frame(self)
        prog_frame.pack(fill='x', padx=5, pady=(10, 0))
        self.folder_label = ttk.Label(prog_frame, text='')
        self.folder_label.pack(anchor='w')
        self.file_progress = ttk.Progressbar(prog_frame, mode='determinate')
        self.file_progress.pack(fill='x', pady=(2, 0))

        # ============ Лог ============
        log_frame = ttk.LabelFrame(self, text='Лог выполнения')
        log_frame.pack(fill='both', expand=True, padx=5, pady=(10, 5))
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, state='disabled', wrap='word'
        )
        self.log_text.pack(fill='both', expand=True)

        # ============ Инициализация ============
        self.load_config()
        if not self.folder_rows:
            self.add_folder()

        self._update_test_button_text()
        self._update_prefix_buttons()

        self.after(100, self._poll_queue)

    # ----- folders -----

    def add_folder(self, config: Optional[dict] = None):
        row = FolderRow(self.scroll.inner_frame, self, config)
        # Всегда держим кнопку "+ Добавить папку" под последней строкой
        self.add_btn.pack_forget()
        self.add_btn.pack(anchor='w', padx=2, pady=(4, 0))
        self.folder_rows.append(row)
        self._update_test_button_text()
        self.scroll._update_scrollregion()

    def remove_folder(self, row: FolderRow):
        if row in self.folder_rows:
            self.folder_rows.remove(row)
        row.frame.destroy()
        self._update_test_button_text()
        self.scroll._update_scrollregion()

    def _update_prefix_buttons(self):
        for row in self.folder_rows:
            row.update_enabled_state()

    def _update_test_button_text(self):
        if not hasattr(self, 'test_btn'):
            return
        text = 'Тестировать источники' if len(self.folder_rows) > 1 else 'Тестировать источник'
        self.test_btn.config(text=text)

    # ----- output -----

    def browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_var.set(d)

    def _validate_output_not_source(self, folders: List[dict], output: str) -> bool:
        """Проверяет, что папка результата не совпадает ни с одним источником."""
        if not output:
            return True
        try:
            out_resolved = Path(output).resolve()
        except Exception:
            return True  # не можем разрешить путь - пропускаем
        for fc in folders:
            path = fc.get('path', '').strip()
            if not path:
                continue
            try:
                src_resolved = Path(path).resolve()
            except Exception:
                continue
            if src_resolved == out_resolved:
                messagebox.showerror(
                    "Ошибка",
                    f"Папка результата не должна совпадать с источником:\n{path}"
                )
                return False
        return True

    # ----- button state helpers -----

    def _set_start_enabled(self, enabled: bool):
        if enabled:
            self.start_btn.config(state='normal', bg=COLOR_GREEN, fg='white')
        else:
            self.start_btn.config(state='disabled', bg=COLOR_GRAY, fg=COLOR_GRAY_FG)

    def _set_test_enabled(self, enabled: bool):
        if enabled:
            self.test_btn.config(state='normal', bg=COLOR_YELLOW, fg='black')
        else:
            self.test_btn.config(state='disabled', bg=COLOR_GRAY, fg=COLOR_GRAY_FG)

    def _set_stop_enabled(self, enabled: bool):
        if enabled:
            self.stop_btn.config(state='normal', bg=COLOR_RED, fg='white')
        else:
            self.stop_btn.config(state='disabled', bg=COLOR_GRAY, fg=COLOR_GRAY_FG)

    # ----- run/stop -----

    def _collect_folders(self) -> List[dict]:
        folders = []
        for row in self.folder_rows:
            cfg = row.to_config()
            if cfg['path']:
                folders.append(cfg)
        return folders

    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror("Ошибка", "Укажите папку, куда копировать обработанные файлы")
            return
        folders = self._collect_folders()
        if not folders:
            messagebox.showerror("Ошибка", "Не выбрано ни одной папки")
            return
        if not self._validate_output_not_source(folders, output):
            return
        self._start_worker(folders, output, testonly=False)

    def start_test(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        folders = self._collect_folders()
        if not folders:
            messagebox.showerror("Ошибка", "Не выбрано ни одной папки")
            return
        output = self.output_var.get().strip() or None
        if output and not self._validate_output_not_source(folders, output):
            return
        self._start_worker(folders, output, testonly=True)

    def _start_worker(self, folders, output, testonly):
        # очистка лога перед запуском
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')
        self.file_progress['value'] = 0
        self.folder_label.config(text="")

        self.save_config()

        self.cancel_event.clear()
        self._set_start_enabled(False)
        self._set_test_enabled(False)
        self._set_stop_enabled(True)

        add_prefixes = self.add_prefixes_var.get()
        transliterate_names = self.transliterate_names_var.get()
        transliterate_id3 = self.transliterate_id3_var.get()

        self.worker_thread = threading.Thread(
            target=self._run_batch_worker,
            args=(folders, output, testonly,
                  add_prefixes, transliterate_names, transliterate_id3),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_batch_worker(self, folders, output_dir, testonly,
                          add_prefixes, transliterate_names, transliterate_id3):
        out_writer = QueueWriter(self.log_queue, 'out')
        err_writer = QueueWriter(self.log_queue, 'err')
        try:
            with contextlib.redirect_stdout(out_writer), \
                 contextlib.redirect_stderr(err_writer):
                try:
                    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    mode = "ТЕСТОВЫЙ режим" if testonly else "Боевой режим"
                    safe_stdout_write(f"[{ts}] Запуск пакетной обработки ({mode}, папок: {len(folders)})\n")
                    run_batch(
                        folders, output_dir, testonly,
                        add_prefixes=add_prefixes,
                        transliterate_names=transliterate_names,
                        transliterate_id3=transliterate_id3,
                        cancel_event=self.cancel_event,
                        progress_callback=self._file_progress_cb,
                        folder_progress_callback=self._folder_progress_cb,
                    )
                except Exception as e:
                    safe_stderr_write(f"Критическая ошибка: {e}\n")
                    traceback.print_exc(file=sys.stderr)
        finally:
            self.log_queue.put(('done', None))

    def _file_progress_cb(self, current: int, total: int):
        self.log_queue.put(('file_progress', (current, total)))

    def _folder_progress_cb(self, current: int, total: int, path: str):
        self.log_queue.put(('folder_progress', (current, total, path)))

    def stop(self):
        self.cancel_event.set()

    # ----- queue polling -----

    def _poll_queue(self):
        while True:
            try:
                kind, data = self.log_queue.get_nowait()
            except queue.Empty:
                break
            try:
                if kind in ('out', 'err'):
                    self._append_log(data)
                elif kind == 'file_progress':
                    cur, tot = data
                    if tot > 0:
                        self.file_progress['maximum'] = tot
                        self.file_progress['value'] = cur
                elif kind == 'folder_progress':
                    cur, tot, path = data
                    if cur >= tot:
                        self.folder_label.config(text="Готово")
                    else:
                        self.folder_label.config(text=f"Папка {cur + 1}/{tot}: {path}")
                elif kind == 'done':
                    self._on_finish()
            except Exception:
                pass
        self.after(100, self._poll_queue)

    def _append_log(self, text: str):
        self.log_text.config(state='normal')
        self.log_text.insert('end', text)
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _on_finish(self):
        self._set_start_enabled(True)
        self._set_test_enabled(True)
        self._set_stop_enabled(False)
        self.file_progress['value'] = 0

    # ----- config -----

    def load_config(self):
        path = get_config_path()
        if not path.exists() or not HAS_YAML:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            common = cfg.get('common') or {}
            self.add_prefixes_var.set(bool(common.get('add_prefixes', True)))
            self.transliterate_names_var.set(bool(common.get('transliterate_names', True)))
            self.transliterate_id3_var.set(bool(common.get('transliterate_id3', True)))

            folders = cfg.get('folders') or []
            for fc in folders:
                if isinstance(fc, dict):
                    self.add_folder(fc)
        except Exception as e:
            safe_stderr_write(f"Ошибка загрузки конфига '{path}': {e}\n")

    def save_config(self):
        if not HAS_YAML:
            return
        path = get_config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            folders = [row.to_config() for row in self.folder_rows
                       if row.path_var.get().strip()]
            cfg = {
                'common': {
                    'add_prefixes': self.add_prefixes_var.get(),
                    'transliterate_names': self.transliterate_names_var.get(),
                    'transliterate_id3': self.transliterate_id3_var.get(),
                },
                'folders': folders,
            }
            with open(path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            safe_stderr_write(f"Ошибка сохранения конфига '{path}': {e}\n")


# ====================== CLI / main ======================

def _run_cli(argv: List[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description='Транслитерация имён музыкальных файлов и ID3-тегов.'
    )
    parser.add_argument('paths', nargs='+', help='Каталоги для обработки')
    parser.add_argument('--ge-1000', action='store_true',
                        help='Префиксы в диапазоне 1000-9999')
    parser.add_argument('--only-prefixes', action='store_true',
                        help='Только добавлять/менять числовые префиксы (без транслитерации)')
    parser.add_argument('--only-transliterate', action='store_true',
                        help='Только транслитерировать (без префиксов)')
    parser.add_argument('--no-prefixes', action='store_true',
                        help='Не добавлять числовые префиксы')
    parser.add_argument('--no-transliterate-names', action='store_true',
                        help='Не транслитерировать имена файлов')
    parser.add_argument('--no-id3', action='store_true',
                        help='Не обрабатывать ID3-теги')
    parser.add_argument('--recursive', action='store_true',
                        help='Обрабатывать вложенные папки')
    parser.add_argument('--testonly', action='store_true',
                        help='Тестовый режим (без реальных изменений)')
    parser.add_argument('--output-dir', default=None,
                        help='Копировать результат в указанную папку (исходники не меняются)')
    args = parser.parse_args(argv)

    add_prefixes = True
    transliterate_names = True
    transliterate_id3 = True

    if args.only_prefixes:
        transliterate_names = False
        transliterate_id3 = False
    if args.only_transliterate:
        add_prefixes = False
    if args.no_prefixes:
        add_prefixes = False
    if args.no_transliterate_names:
        transliterate_names = False
    if args.no_id3:
        transliterate_id3 = False

    exit_code = 0
    for path in args.paths:
        try:
            run_operation(
                path,
                ge_1000=args.ge_1000,
                add_prefixes=add_prefixes,
                transliterate_names=transliterate_names,
                transliterate_id3=transliterate_id3,
                testonly=args.testonly,
                output_dir=args.output_dir,
                recursive=args.recursive,
            )
        except RuntimeError as e:
            safe_stderr_write(f"Ошибка: {e}\n")
            exit_code = 1
    return exit_code


def main() -> int:
    if len(sys.argv) > 1:
        return _run_cli(sys.argv[1:])

    if not HAS_TK:
        safe_stderr_write("Ошибка: tkinter не установлен. GUI недоступен.\n")
        return 1
    if not HAS_YAML:
        safe_stderr_write("Предупреждение: PyYAML не установлен. "
                          "Конфиг сохраняться не будет.\n")

    try:
        app = App()
    except Exception as e:
        safe_stderr_write(f"Не удалось запустить GUI: {e}\n")
        traceback.print_exc(file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())