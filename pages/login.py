import asyncio
from typing import Optional, Any

import httpx
from playwright.async_api import BrowserContext, Page

from base.base_crawler import AbstractLogin
from pages.exception import PasswordException
from tools import utils


class Login(AbstractLogin):
    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = "",
                 account: list = []
                 ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        self.account = account

    async def begin(self):
        """Start login bilibili"""
        utils.logger.info("[Login.begin] Begin login Bilibili ...")
        # select login type
        if self.login_type == "qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "phone":
            await self.login_by_mobile()
        elif self.login_type == "account":
            await self.login_by_account()
        elif self.login_type == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[Login.begin] Invalid Login Type Currently only supported qrcode or phone or cookie ...")

        pass

    async def login_by_account(self):
        if len(self.account) != 2:
            raise ValueError(
                "[Login.begin] Invalid Login Type params len 2")
        await self.context_page.wait_for_selector("xpath=//*[@id='admin_name']")
        username_input_ele = self.context_page.locator("xpath=//*[@id='admin_name']")
        await username_input_ele.fill(self.account[0])
        await asyncio.sleep(0.5)
        password_input_ele = self.context_page.locator("xpath=//*[@id='admin_password']")
        await password_input_ele.fill(self.account[1])
        bun_ele = self.context_page.locator("css=#main-container button.btn-alt-primary")
        await bun_ele.click()
        try:
            e = self.context_page.locator("css=#sanlan2")
            s = await e.inner_html(timeout=2000)
            if not 'ico_pre.png' in s:
                raise PasswordException("登录超时,密码错误")
        except Exception as ex:
            if "Timeout" in str(ex):
                raise PasswordException("登录超时,密码错误")
            else:
                raise ex


    async def login_by_qrcode(self):
        pass

    async def login_by_mobile(self):
        pass

    async def login_by_cookies(self):
        utils.logger.info("[Login.login_by_cookies] Begin login  by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".gdcxxy.net",
                'path': "/"
            }])

    async def request(self, method, url, **kwargs) -> Any:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=5000,
                **kwargs
            )
        data: str = response.text
        return data
