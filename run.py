import asyncio

from bot.main import FunBot


async def main():
    bot = FunBot()
    await bot.start(bot.config['token'])

if __name__ == '__main__':
    asyncio.run(main())
