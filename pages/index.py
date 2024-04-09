import asyncio
import os
from typing import Optional, Dict, Tuple, List

from httpx import ReadTimeout, ConnectTimeout
from playwright.async_api import BrowserType, BrowserContext, Page, async_playwright

import config
from base.base_crawler import AbstractCrawler
from pages.client import Client
from pages.exception import DataFetchError, Over10Exception, FaceCollectionException, PasswordException, VerifyException
from pages.login import Login
from proxy.proxy_ip_pool import create_ip_pool
from proxy.proxy_ip_provider import IpInfoModel
from store.store import StoreRemoteImpl
from tools import utils


async def verify_callback(ctx, obj, queue):
    await queue.put(obj)


async def verify(callback):
    queue = asyncio.Queue()  # 创建一个异步队列用于接收回调参数
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.vc90.cn/home.html")
        # 将队列传递给回调函数
        await page.expose_binding("callback", lambda ctx, result: verify_callback(ctx, result, queue))
        await page.evaluate("window.CaptchaId_yz()")
        await asyncio.sleep(3)
        await page.close()
        await browser.close()
        # 从队列中获取回调参数
        while not queue.empty():
            obj = await queue.get()
            print("Received callback parameter:", obj)
            return obj


class Index(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    account: list
    context_page: Page
    client: Client
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        self.login_url = "https://chengkao.gdcxxy.net/gdcx/login2.php"
        self.index_url = "https://chengkao.gdcxxy.net/gdcx/mycourse.php"

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[Crawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % self.platform)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    def init_config(self, platform: str, login_type: str, crawler_type: str, account: list):
        self.platform = platform
        self.login_type = login_type
        self.crawler_type = crawler_type
        self.account = account

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                None,
                self.user_agent,
                headless=config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            # await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)
            # Create a client to interact with the xiaohongshu website.
            self.client = await self.create_client(httpx_proxy_format)
            if not await self.client.pong():
                login_obj = Login(
                    login_type=self.login_type,
                    login_phone="",  # your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                    account=self.account
                )
                store = StoreRemoteImpl()
                username = self.account[0]
                # 执行了视频任务 出现 over10 异常停止
                try:
                    await login_obj.begin()
                    await self.client.update_cookies(browser_context=self.browser_context)
                    is_success = await self.get_specified_videos()
                    if is_success:
                        await store.set_user_finish(username)
                except FaceCollectionException as ex:
                    await store.set_user_password_error(username)
                    utils.logger.info(f"[Crawler.FaceCollectionException] Crawler fail ...{ex}")
                except PasswordException as ex:
                    await store.set_user_password_error(username)
                    utils.logger.error(f"[Crawler.PasswordException] Crawler fail ...{ex}")
                except Over10Exception as ex:
                    utils.logger.error(f"[Crawler.Over10Exception] Crawler fail ...{ex}")
                    await store.set_user_over_10(username)

            utils.logger.info("[Crawler.start] Crawler finished ...")

    async def get_specified_videos(self):
        """
        get specified videos info
        :return:
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        course_list: List[Dict] = await self.client.get_course_list()
        task_list = [
            self.get_video_info_task(course_item.get("id"), semaphore) for course_item in course_list
        ]
        # 异步获取所有课程下的视频返回类型[[],[]]
        video_all = await asyncio.gather(*task_list)
        for videos_sub in video_all:
            for video in videos_sub:
                # 视频状态是未完成
                if not video.get("stat"):
                    await self.fuck_video_task(video.get("id"))
        return True

    async def get_video_info_task(self, course_id: str, semaphore: asyncio.Semaphore) -> Optional[List[Dict]]:
        """
        根据课程id返回课程下的视频列表
        :param course_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.client.get_video_list(course_id=course_id)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{course_id}, err: {ex}")
                return None

    async def fuck_video_task(self, video_id: str):
        """
        视频播放心跳
        :param video_id:
        :return:
        """
        try:
            utils.logger.info(f"[Crawler.fuck_video] begin get video_id: {video_id}")
            video_info = await self.client.get_video_info(video_id)
            current_time = int(video_info.get("max_time")) + 5
            while True:
                r = await self.client.fuck_video(
                    video_info.get("type_id"),
                    video_info.get("video_id"),
                    str(current_time),
                    video_info.get("user_log_id")
                )
                utils.logger.info(
                    f"[Crawler.fuck_video] success current time <{r}>/<{video_info['length']}> video_id: {video_id} ")
                if 'video_yz' in r:
                    # 尝试3次拿凭证
                    res = None
                    for i in range(3):
                        res = await verify(verify_callback)
                        if res:
                            break
                    if res:
                        v = await self.client.verify(res['ticket'], res['randstr'], video_info.get("type_id"),
                                                     video_info.get("video_id"))
                        utils.logger.info(f"[Crawler.fuck_video] result <{v}> video_id: {video_id} ")
                    else:
                        raise VerifyException("VTT验证异常")

                elif 'over10' in r or 'other' in r:
                    raise Over10Exception("视频已达到最大")
                else:
                    remote_time = int(r.strip('\ufeff'))
                    if remote_time >= video_info['length']:
                        break
                    current_time = remote_time + 5

                await asyncio.sleep(5.2)
        except DataFetchError as ex:
            utils.logger.error(f"[Crawler.fuck_video_task] get video_id: {video_id}  error: {ex}")
        pass

    async def create_client(self, httpx_proxy: Optional[str]) -> Client:
        """Create xhs client"""
        utils.logger.info("[Crawler.create_client] Begin create  API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        client_obj = Client(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://chengkao.gdcxxy.net",
                "Referer": "https://chengkao.gdcxxy.net",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return client_obj

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy
