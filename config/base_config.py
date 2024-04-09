PLATFORM = "chengkao"
KEYWORDS = "python,golang"
LOGIN_TYPE = "account"  # qrcode or phone or cookie account
COOKIES = ""
CRAWLER_TYPE = "video"  # 爬取类型，search(关键词搜索) | detail(帖子相亲)| creator(创作者主页数据)

# 登录用户
ACCOUNT = [
    '450922198412111565',
    '111565'
]

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 设置为True不会打开浏览器（无头浏览器），设置False会打开一个浏览器（小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码）
HEADLESS = True

# 是否保存登录状态
SAVE_LOGIN_STATE = False

# 数据保存类型选项配置,支持三种类型：csv、db、json
SAVE_DATA_OPTION = "json"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 2
