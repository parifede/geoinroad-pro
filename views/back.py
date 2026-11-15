from typing import Awaitable, Callable

import flet as ft


def back_handler(on_back: Callable[[], Awaitable[None]] | None):
    """Gestore del tasto back di Android per una vista con can_pop=False.

    La vista non viene mai chiusa dal sistema (confirm_pop(False)): decide
    l'app cosa fare, per esempio tornare al diario. Senza on_back il tasto
    non fa nulla.
    """

    async def handle(e: ft.ControlEvent) -> None:
        await e.control.confirm_pop(False)
        if on_back is not None:
            await on_back()

    return handle
