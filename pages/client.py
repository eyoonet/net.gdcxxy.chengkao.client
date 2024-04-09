import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from urllib.parse import urlencode

import httpx
from httpx import ReadTimeout, ConnectTimeout, ConnectError
from playwright.async_api import BrowserContext, Page, async_playwright

from base.base_crawler import AbstractApiClient
from tools import utils
from .exception import DataFetchError, FaceCollectionException
from bs4 import BeautifulSoup


def get_id(text):
    pattern = r"gotoxx\('.*?','(.*?)'\);"
    match = re.search(pattern, text)

    if match:
        dynamic_variable = match.group(1)
        return dynamic_variable
    else:
        print("未找到动态变量")


class Client(AbstractApiClient):
    def __init__(
            self,
            timeout=20,
            proxies=None,
            *,
            headers: Dict[str, str],
            playwright_page: Page,
            cookie_dict: Dict[str, str],
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://chengkao.gdcxxy.net"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def request(self, method, url, **kwargs) -> Any:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            error = True
            # 错误补发
            for i in range(3):
                try:
                    response = await client.request(
                        method, url, timeout=self.timeout,
                        **kwargs
                    )
                    error = False
                    break
                except ReadTimeout as ex:
                    await asyncio.sleep(1)
                    utils.logger.error(
                        f"[Crawler.ReadTimeout] re req {url} number {i}")
                except ConnectTimeout as ex:
                    await asyncio.sleep(1)
                    utils.logger.error(
                        f"[Crawler.ConnectTimeout] re req {url} number {i}")
                except ConnectError as ex:
                    await asyncio.sleep(1)
                    utils.logger.error(
                        f"[Crawler.ConnectError] re req {url} number {i}")
            if error:
                raise DataFetchError("Request Timeout")
        data: str = response.text
        return data

    async def get(self, uri: str, params=None) -> str:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=self.headers)

    async def post(self, uri: str, data: dict) -> Dict:
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}",
                                  data=json_str, headers=self.headers)

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[BilibiliClient.pong] Begin pong bilibili...")
        ping_flag = False
        try:
            check_login_uri = "/gdcx/mycourse.php"
            body = await self.get(check_login_uri)
            if "top.location.href=\'/gdcx/login2.php\'" not in body:
                utils.logger.info("[Client.pong] Use cache login state get web interface successfull!")
                ping_flag = True
        except Exception as e:
            utils.logger.error(f"[Client.pong] Pong bilibili failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def get_course_list(self, callback: Optional[Callable] = None) -> list:
        utils.logger.info("[Client.get_course_list] Begin ...")
        course_list_uri = "/gdcx/mycourse.php"
        body = await self.get(course_list_uri)
        if "您还未完成照片采集，请前往采集页面，点击“人脸采集”" in body:
            raise FaceCollectionException(body)

        el = BeautifulSoup(body, 'html.parser')
        course_list_el = el.select(".itemBox.row")
        course_result = []
        for course_item in course_list_el:
            _id = get_id(course_item.select_one(".but_study").attrs['onclick'])
            title = course_item.find("h1").get_text()
            k = course_item.select(".numbox span p.text-666")
            v = course_item.select(".numbox span p.number")
            score = []
            for i in range(len(k)):
                score.append({k[i].get_text(): v[i].get_text()})
            result = {"id": _id, "title": title, "score": score}
            course_result.append(result)
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(result)
        return course_result

    async def get_video_list(self, course_id: str, callback: Optional[Callable] = None) -> List[Dict]:
        utils.logger.info(f"[Client.get_video_list] Begin Id is {course_id}")
        url = "/gdcx/jp_wiki_study.php?kcdm=" + course_id
        body = await self.get(url)
        el = BeautifulSoup(body, 'html.parser')
        li_el = el.select("#side-overlay li")
        video_result = []
        # totalSeconds = hours * 3600 + minutes * 60 + seconds;
        for li in li_el:
            _id = li.select_one("a").attrs['href']
            name = li.select_one("span").get_text()
            stat = True if li.select_one("span").attrs['style'] == "color:#00A600;" else False
            progress = li.select_one("div:nth-child(3)").get_text()
            result = {
                "id": _id,
                "name": name,
                "progress": progress,
                "stat": stat
            }
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(result)
            video_result.append(result)
        return video_result

    async def get_video_info(self, id: str, callback: Optional[Callable] = None) -> Dict:
        """
           <input type="hidden" id="max_jindu" value="1926"/>
            <input type="hidden" id="cur_jindu_old" value="1926"/>
            <input type="hidden" id="cur_jindu" value="1926"/>
            <input type="hidden" id="jjwikiid" value="20832"/>
            <input type="hidden" id="TypeId" value="5106"/>

            <input type="hidden" id="shichang" value="2610"/>
            <input type="hidden" id="is_kt" value="0"/>
            <input type="hidden" id="is_zy" value="0"/>
            <input type="hidden" id="isnot_st" value="1"/>
            <input type="hidden" id="cpidlist" value="19441"/>
            <input type="hidden" id="userid" value="125798"/>

            <input type="hidden" id="is_xuewan" value="0"/>
            <input type="hidden" id="next_jjwikiid" value="0"/>
            <input type="hidden" id="is_zhyz" value="0"/>
            <input type="hidden" id="is_tishi" value="0"/>
        """
        utils.logger.info(f"[Client.get_video_info] Begin Id is {id}")
        url = f"/gdcx/{id}"
        body = await self.get(url)
        if "1、为保证学习效果" not in body:
            raise DataFetchError(id)

        el = BeautifulSoup(body, 'html.parser')
        s = el.select_one(".si-control-play +div +div").get_text()
        match = re.search(r'/(\d{2}:\d{2}:\d{2})', s)
        seconds = 0
        if match:
            time = match.group(1)
            time_obj = datetime.strptime(time, '%H:%M:%S')
            seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        max_time = el.select_one("#max_jindu").attrs['value']
        current_time = el.select_one("#cur_jindu").attrs['value']
        type_id = el.select_one("#TypeId").attrs['value']
        length = seconds #el.select_one("#shichang").attrs['value']
        video_id = el.select_one("#jjwikiid").attrs['value']
        user_log_id = el.select_one("#userlog_id").attrs['value']
        finish = el.select_one("#is_xuewan").attrs['value']

        return {
            "max_time": max_time,
            "current_time": current_time,
            "type_id": type_id,
            "length": length,
            "video_id": video_id,
            "user_log_id":user_log_id,
            "finish": finish
        }

    async def fuck_video(self, type_id: str, video_id:str, current_time:str,user_log_id:str):
        url = f"/gdcx/learn_jjsp.action.php?TypeId={type_id}&jjwikiid={video_id}&cur_jindu={current_time}&userlog_id={user_log_id}"
        headers = self.headers.copy()
        headers['X-Requested-With'] = "XMLHttpRequest"
        result = await self.request(method="GET", url=f"{self._host}{url}", headers=headers)
        return result

    async def verify(self,ticket,randstr,type_id,video_id):
        url = "https://chengkao.gdcxxy.net/gdcx/jp_study.action.php"
        req = {
            "ticket": ticket,
            "randstr":randstr,
            "TypeId": type_id,
            "jjwikiid":video_id
        }
        headers = self.headers.copy()
        headers['Content-Type'] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers['X-Requested-With'] = "XMLHttpRequest"
        result = await self.request(method="POST", url=url, headers=headers,data=req)
        return result