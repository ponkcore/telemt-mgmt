"""Allow running the bot via ``python -m bot``.

Delegates to ``bot.main.main()`` so that ``python -m bot`` starts the
standalone bot with long polling (AC1).
"""

from bot.main import main

if __name__ == "__main__":
    main()
