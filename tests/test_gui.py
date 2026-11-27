"""GUI smoke-тест: окно создаётся, отрисовывается и закрывается.

Полноценный mainloop не запускаем — он заблокировал бы тестовый прогон.
Тест помечен маркером `gui`; без дисплея (или без tkinter) он пропускается.
"""

import queue

import pytest


@pytest.mark.gui
def test_app_can_be_created(entry_module):
    if not entry_module.HAS_TK:
        pytest.skip('tkinter не установлен')

    try:
        app = entry_module.App()
    except Exception as exc:  # например, TclError без дисплея
        pytest.skip(f'GUI недоступен: {exc}')

    try:
        app.withdraw()
        app.update_idletasks()
        app.update()
        assert app.title()
        assert isinstance(app.log_queue, queue.Queue)
    finally:
        app.destroy()
