import argparse
import asyncio
import os
import socket
import sys

import httpx

from pages.index import Index
import config
from base.base_crawler import AbstractCrawler


class CrawlerFactory:
    CRAWLERS = {
        "chengkao": Index,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy or ks or bili ...")
        return crawler_class()


async def get_account(number: int):
    hostname = socket.gethostname() + "_" + str(number)
    async with httpx.AsyncClient() as client:
        response = await client.request("get",
                                        f"https://que.kunzejiaoyu.cn/dev-api/api/cx/student/info?code={hostname}",
                                        timeout=3000)
        return response.json()


async def main():
    # define command line params ...
    parser = argparse.ArgumentParser(description='crawler program.')
    parser.add_argument('--platform', type=str, help='platform select (chengkao)',
                        choices=["chengkao"], default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie | account | auto)',
                        choices=["qrcode", "phone", "cookie", "account", 'auto'], default=config.LOGIN_TYPE)
    parser.add_argument('--type', type=str, help='crawler type (video | question | exam)',
                        choices=["video", "question", "exam"], default=config.CRAWLER_TYPE)
    parser.add_argument('--u', type=str, help='--u admin 123456', nargs=2, default=config.ACCOUNT)

    parser.add_argument('--id', type=int, help='--id 1', default=0)

    args = parser.parse_args()

    if args.lt == 'auto':
        account = await get_account(args.id)
        args.u = [account.get("data").get("userName"), account.get("data").get("password")]
        args.lt = "account"

    crawler = CrawlerFactory.create_crawler(platform=args.platform)
    crawler.init_config(
        platform=args.platform,
        login_type=args.lt,
        crawler_type=args.type,
        account=args.u
    )
    await crawler.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
        # asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
