"""aiogram Router for the "Get Proxy" user flow.

This module exposes ``create_router()``, a factory function that returns
a configured ``aiogram.Router`` with handlers for:

- ``/start`` command — sends a welcome message with an inline keyboard
  containing a "Получить прокси" (Get Proxy) button.
- ``get_proxy`` callback query — the main flow: hashes the Telegram ID,
  checks the DB for an existing user, creates a telemt user if none exists,
  builds the proxy link, generates a QR code, and sends both to the user.

Per ADR-001@0.1.2 (Embeddable Package Architecture):
    - No global state, no singletons, no module-level side effects (INV-EMBED).
    - All dependencies are injected via ``create_router()`` parameters.
    - The returned Router can be included in any aiogram 3.x Dispatcher
      with ``dp.include_router(router)``.

Per INV-HASH:
    - Telegram IDs are never stored or sent to telemt in raw form.
    - ``hash_telegram_id()`` is called to produce the 16-char telemt username.
    - ``hash_telegram_id_full()`` is called to produce the 64-char dedup hash.

Per INV-DOMAIN:
    - The ``server=`` field in proxy links uses the domain name from
      ``ProxyConfig.server``, never a raw IP.

R18 Extension Point:
    - ``create_router()`` accepts an optional ``tier_service=None`` parameter.
    - When ``None`` (the default), all users receive the same server-level
      ad_tag. This is the MVP behaviour.
    - When a ``TierService`` is provided (future), it would route users
      to different ad_tags based on their tier. This is NOT implemented
      in MVP — only the extension point (clean interface boundary) exists.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from telemt_proxy.hashing import hash_telegram_id, hash_telegram_id_full
from telemt_proxy.link import build_proxy_link
from telemt_proxy.models import ProxyUser
from telemt_proxy.qr import generate_qr

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from telemt_proxy.client import TelemtClient
    from telemt_proxy.config import ProxyConfig
    from telemt_proxy.schemas import TelemtUser


class TierServiceProtocol(Protocol):
    """Protocol for the R18 tier service extension point.

    This protocol defines the interface that a future ``TierService``
    implementation must satisfy. It is NOT implemented in MVP —
    ``create_router()`` accepts ``tier_service=None`` as the default.

    When implemented, the tier service would:
    1. Check user tier (Bedolaga Web API lookup by Telegram ID hash).
    2. Apply per-user ad_tag (telemt's ``user_ad_tags`` config).
    3. Apply per-user quota limits.
    """

    async def get_ad_tag_for_user(self, telegram_id_hash: str) -> str | None:
        """Return the ad_tag for the given user, or None for server default.

        Args:
            telegram_id_hash: The full SHA256 hash of the Telegram ID.

        Returns:
            The ad_tag string for this user's tier, or ``None`` to use
            the server-level default ad_tag.
        """
        ...


def create_router(
    telemt_client: TelemtClient,
    db_session_factory: async_sessionmaker[AsyncSession],
    config: ProxyConfig,
    tier_service: TierServiceProtocol | None = None,
) -> Router:
    """Create and return a configured aiogram Router.

    The router handles the "Get Proxy" user flow:
    ``/start`` → inline keyboard → ``get_proxy`` callback → create/retrieve
    telemt user → build proxy link → generate QR → send link + QR.

    All dependencies are injected — no global state, no module-level
    side effects (INV-EMBED, ADR-001).

    Args:
        telemt_client: The ``TelemtClient`` for telemt REST API calls.
        db_session_factory: SQLAlchemy async session factory for DB access.
        config: ``ProxyConfig`` with server, port, salt, and API config.
        tier_service: Optional R18 extension point for future user-tier
            routing. When ``None`` (the default), all users receive the
            same server-level ad_tag. NOT implemented in MVP.

    Returns:
        A configured ``aiogram.Router`` ready to be included in any
        aiogram 3.x Dispatcher via ``dp.include_router(router)``.
    """
    router = Router()

    # Inline keyboard with "Получить прокси" button.
    def _get_proxy_keyboard() -> InlineKeyboardMarkup:
        """Build the inline keyboard with the 'Get Proxy' button."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Получить прокси",
                        callback_data="get_proxy",
                    ),
                ],
            ],
        )

    @router.message(Command("start"))
    async def _handle_start(message: Message) -> None:
        """Handle the /start command — send welcome + inline keyboard."""
        await message.answer(
            "Привет! Нажмите кнопку, чтобы получить прокси.",
            reply_markup=_get_proxy_keyboard(),
        )

    @router.callback_query(F.data == "get_proxy")
    async def _handle_get_proxy(callback: CallbackQuery) -> None:
        """Handle the 'get_proxy' callback — the main proxy-link flow.

        Flow:
        1. Hash the Telegram ID (INV-HASH — never store/send raw IDs).
        2. Check DB for an existing ProxyUser by telegram_id_hash.
        3. If found → retrieve the telemt user to get the current secret.
        4. If not found → create a telemt user via TelemtClient.create_user(),
           then store the ProxyUser in the DB.
        5. Build the proxy link (INV-DOMAIN — domain in server=).
        6. Generate a QR code PNG.
        7. Send the link text + QR code image to the user.
        """
        if callback.message is None or callback.from_user is None:
            await callback.answer("Ошибка: не удалось определить пользователя.")
            return

        # The message that triggered the callback — used for sending replies.
        # In aiogram 3.x, callback.message is Union[Message, InaccessibleMessage]
        # at the type level, but for inline keyboards attached to accessible
        # messages it is always Message. The None check above guards against
        # the inaccessible case; the assignment is safe.
        message: Message = callback.message  # type: ignore[assignment]
        telegram_id: int = callback.from_user.id

        # Step 1: Hash the Telegram ID (INV-HASH).
        telemt_username: str = hash_telegram_id(telegram_id, config.salt)
        telegram_id_hash: str = hash_telegram_id_full(telegram_id, config.salt)

        # Step 2: Check DB for an existing user (deduplication).
        async with db_session_factory() as session:
            result = await session.execute(
                select(ProxyUser).where(
                    ProxyUser.telegram_id_hash == telegram_id_hash,
                ),
            )
            existing_user: ProxyUser | None = result.scalar_one_or_none()

            if existing_user is not None:
                # Step 3: User exists — retrieve current secret from telemt.
                telemt_user: TelemtUser = await telemt_client.get_user(
                    existing_user.telemt_username,
                )
                secret: str = telemt_user.secret or ""
            else:
                # Step 4: New user — create via TelemtClient (INV-HASH:
                # only the hash is sent to telemt, never the raw ID).
                telemt_user = await telemt_client.create_user(telemt_username)
                secret = telemt_user.secret or ""

                # Store the ProxyUser in the DB for future dedup.
                new_proxy_user = ProxyUser(
                    telemt_username=telemt_username,
                    telegram_id_hash=telegram_id_hash,
                    source="bot",
                    is_active=True,
                )
                session.add(new_proxy_user)
                await session.commit()

        # Step 5: Build the proxy link (INV-DOMAIN — domain in server=).
        proxy_link: str = build_proxy_link(
            server=config.server,
            port=config.port,
            secret=secret,
        )

        # Step 6: Generate QR code PNG.
        qr_png: bytes = await asyncio.to_thread(generate_qr, proxy_link)

        # Step 7: Send link text + QR code image.
        await message.answer(
            f"Ваша ссылка на прокси:\n\n{proxy_link}",
        )
        await message.answer_photo(
            BufferedInputFile(qr_png, filename="proxy_qr.png"),
            caption="Отсканируйте QR-код для подключения:",
        )

        await callback.answer()

    # Note: tier_service is an R18 extension point. When None (the default),
    # all users receive the same server-level ad_tag. Future implementations
    # would use it to route users to different ad_tags based on tier.
    # This is intentionally not wired into the flow above — it is a clean
    # interface boundary only (ADR-001, ARCH-001 §4 R18 Extension Point).
    _ = tier_service  # acknowledged: future use

    return router
