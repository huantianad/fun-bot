import asyncio

from bot.main import FunBot


async def main():
    bot = FunBot()
    await bot.start(bot.token)

if __name__ == '__main__':
    asyncio.run(main())
