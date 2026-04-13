"""CLI entry points for HomeView server management."""
import asyncio


def start() -> None:
    """homeview start — run the HomeView server."""
    import uvicorn
    from server.config import get_config

    config = get_config()
    uvicorn.run(
        "server.main:app",
        host=config.host,
        port=config.port,
        reload=False,
    )


def reset_pairing() -> None:
    """homeview reset-pairing — revoke all tokens and print a new pairing code."""
    from server.config import get_config
    from server.db import init_db
    from server.auth.pairing import PairingManager

    config = get_config()

    async def _run() -> None:
        await init_db(config.db_path)
        mgr = PairingManager(config.db_path)
        code = await mgr.reset_pairing()
        print(f"Pairing reset. New code: {code}")

    asyncio.run(_run())
