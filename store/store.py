from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Coroutine

import httpx

from pages.exception import DataFetchError


class IStore(ABC):
    @abstractmethod
    async def get_user_info(self, hostname: str) -> list:
        pass

    @abstractmethod
    async def set_user_over_10(self, username: str):
        pass

    @abstractmethod
    async def set_user_finish(self, username: str):
        pass

    @abstractmethod
    async def set_user_password_error(self, username: str):
        pass


class StoreRemoteImpl(IStore):
    _host: str

    def __init__(
            self,
            timeout=30,
            proxies=None,
            *,
            headers=None
    ):
        if headers is None:
            headers = {
                "Content-Type": "application/json;charset=UTF-8"
            }
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://que.kunzejiaoyu.cn/dev-api"

    async def request(self, method, url, **kwargs) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        data: Dict = response.json()
        if data.get("code") != 200:
            raise DataFetchError(data.get("msg", "unkonw error"))
        else:
            return data.get("data", {})

    async def get(self, uri: str, params: Optional[Dict] = None, headers: Optional[Dict] = None):
        """
        get 请求
        :param uri:
        :param params:
        :param headers:
        :return:
        """
        headers = headers or self.headers
        return await self.request(method="GET", url=f"{self._host}{uri}", params=params, headers=headers)

    async def post(self, uri: str, data: dict, headers: Optional[Dict] = None):
        """
        post 请求
        :param uri:
        :param data:
        :param headers:
        :return:
        """
        headers = headers or self.headers
        return await self.request(method="POST", url=f"{self._host}{uri}", data=data, headers=headers)

    async def post_form(self, uri: str, data: dict, headers: Optional[Dict] = None):
        """
        post 请求
        :param uri:
        :param data:
        :param headers:
        :return:
        """
        headers = headers or self.headers
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        return await self.request(method="POST", url=f"{self._host}{uri}", data=data, headers=headers)

    async def get_user_info(self, hostname: str) -> list:
        """
        获取用户信息
        :param hostname:
        :return:
        """
        data: Dict = await self.get(f"/api/cx/student/info?code={hostname}")
        return [data.get("userName"), data.get("password")]

    async def set_user_over_10(self, username: str):
        """
        视频今日限时
        :param username:
        :return:
        """
        return await self.post_form("/api/cx/student/status/over10", data={"userName": username})

    async def set_user_finish(self, username: str):
        """
        用户完成
        :param username:
        :return:
        """
        return await self.post_form("/api/cx/student/status/finish", data={"userName": username})

    async def set_user_password_error(self, username: str):
        """
        用户异常
        :param username:
        :return:
        """
        return await self.post_form("/api/cx/student/status/error", data={"userName": username})
