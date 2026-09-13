"""Interactive Chrome login with minimal, validated session capture."""

import asyncio
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

from mercadona_mcp.companion.session import (
    SessionMaterial,
    extract_session_material,
    store_session,
)
from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.models import AuthStatus
from mercadona_mcp.security import SecretStore

_CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
_MERCADONA_ORIGIN = "https://tienda.mercadona.es"
_LOGIN_TIMEOUT_SECONDS = 600
_ALLOWED_HOSTS = {"tienda.mercadona.es", "accounts.google.com"}


class LoginService:
    """Run the user-mediated login flow in a disposable Chrome context."""

    def __init__(
        self,
        secret_store: SecretStore,
        *,
        chrome_executable: str = _CHROME_EXECUTABLE,
    ) -> None:
        self._secret_store = secret_store
        self._chrome_executable = chrome_executable

    async def login(self) -> AuthStatus:
        """Capture and validate an authenticated session without reading credentials."""
        if not Path(self._chrome_executable).is_file():
            raise MercadonaMCPError(
                ErrorCode.MERCADONA_UNAVAILABLE,
                "Google Chrome is required for login but was not found.",
            )

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=self._chrome_executable,
                headless=False,
            )
            context = await browser.new_context()
            try:
                page = await context.new_page()
                await page.goto(_MERCADONA_ORIGIN, wait_until="domcontentloaded")
                session, authenticated_page = await _wait_for_authenticated_session(
                    context
                )
                await _validate_session(authenticated_page, session)
                store_session(self._secret_store, session)
                return AuthStatus(connected=True)
            finally:
                await context.close()
                await browser.close()


async def _wait_for_authenticated_session(
    context: BrowserContext,
) -> tuple[SessionMaterial, Page]:
    deadline = asyncio.get_running_loop().time() + _LOGIN_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        for page in context.pages:
            if _allowed_mercadona_page(page):
                raw_session = await page.evaluate("localStorage.getItem('MO-user')")
                if isinstance(raw_session, str):
                    return extract_session_material(raw_session), page
        await asyncio.sleep(1)
    raise MercadonaMCPError(
        ErrorCode.REAUTHENTICATION_REQUIRED,
        "Login timed out. Please run login again and complete it in Chrome.",
    )


def _allowed_mercadona_page(page: Page) -> bool:
    parsed = urlparse(page.url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in _ALLOWED_HOSTS
        and parsed.hostname == "tienda.mercadona.es"
    )


async def _validate_session(page: Page, session: SessionMaterial) -> None:
    """Use the observed safe cart read and return no response body to Python."""
    status = await page.evaluate(
        """async ({ token, userUuid }) => {
            const path = `/api/customers/${encodeURIComponent(userUuid)}/cart/`;
            const response = await fetch(path, {
                headers: { Authorization: `Bearer ${token}` },
            });
            return response.status;
        }""",
        {"token": session.token, "userUuid": session.user_uuid},
    )
    if status != 200:
        raise MercadonaMCPError(
            ErrorCode.REAUTHENTICATION_REQUIRED,
            "Mercadona could not validate the new session. Please run login again.",
        )
