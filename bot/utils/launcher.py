import asyncio
import argparse
from itertools import cycle

from pyrogram import Client, compose
import json
from bot.config import settings
from bot.utils import logger
from bot.core.tapper import run_tapper
from bot.core.registrator import register_sessions
from bot.utils.scripts import get_session_names, get_proxies, load_accounts_data

banner = """

▀▀█▀▀ █▀▀█ █▀▀█ ░█▀▀▀█ █   █ █▀▀█ █▀▀█ ░█▀▀█ █▀▀█ ▀▀█▀▀
 ░█   █▄▄█ █  █  ▀▀▀▄▄ █▄█▄█ █▄▄█ █  █ ░█▀▀▄ █  █   █
 ░█   ▀  ▀ █▀▀▀ ░█▄▄▄█  ▀ ▀  ▀  ▀ █▀▀▀ ░█▄▄█ ▀▀▀▀   ▀

"""

options = """
Select an action:

    1. Create session
    2. Run clicker
    3. Run via Telegram (Beta)
"""


global tg_clients


async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    print(banner)

    # Загружаем аккаунты из JSON
    try:
        with open('accounts.json', 'r') as f:
            accounts = json.load(f)
        accounts_count = len(accounts)
        proxies_count = len([acc for acc in accounts if "proxy" in acc])
        logger.info(f"Detected {len(get_session_names())} sessions | {proxies_count} proxies in accounts.json")
    except FileNotFoundError:
        logger.info(f"Detected {len(get_session_names())} sessions | accounts.json not found")

    action = parser.parse_args().action

    if not action:
        print(options)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ["1", "2", "3"]:
                logger.warning("Action must be 1, 2 or 3")
            else:
                action = int(action)
                break

    if action == 1:
        await register_sessions()
    elif action == 2:
        tg_clients = await get_tg_clients()
        await run_tasks(tg_clients=tg_clients)
    elif action == 3:
        tg_clients = await get_tg_clients()
        logger.info("Send /help command in Saved Messages\n")
        await compose(tg_clients)


async def run_tasks(tg_clients: list[Client]):
    accounts_data = load_accounts_data()
    lock = asyncio.Lock()

    tasks = [
        asyncio.create_task(
            run_tapper(
                tg_client=tg_client,
                account_data=accounts_data.get(tg_client.name, {}),
                lock=lock,
            )
        )
        for tg_client in tg_clients
    ]

    await asyncio.gather(*tasks)
