#!/usr/bin/env python3
import asyncio

from bot import FunBot


async def main():
    bot = FunBot()
    await bot.start(bot.token)

if __name__ == '__main__':
    asyncio.run(main())
