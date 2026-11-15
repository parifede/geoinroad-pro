"""Cronologia delle pagine del portale aperte nel diario.

Serve al tasto back di Android: torna alla pagina precedente del portale,
ma mai alla pagina di login (l'auto-login rientrerebbe da solo) e, se non
c'e' niente prima, non fa nulla.
"""

_LIMIT = 50


class WebHistory:
    def __init__(self) -> None:
        self._urls: list[str] = []

    def visit(self, url: str) -> None:
        url = str(url or "").strip()
        if not url or (self._urls and self._urls[-1] == url):
            return
        self._urls.append(url)
        if len(self._urls) > _LIMIT:
            del self._urls[0]

    def can_go_back(self) -> bool:
        return len(self._urls) >= 2 and "/login" not in self._urls[-2]

    def went_back(self) -> None:
        if len(self._urls) >= 2:
            self._urls.pop()

    def reset(self) -> None:
        self._urls.clear()
