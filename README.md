# 下载微博

## 感谢

原仓库提供大量参考：

- [nondanee/weiboPicDownloader](https://github.com/nondanee/weiboPicDownloader) (original repo)
- [yAnXImIN/weiboPicDownloader](https://github.com/yAnXImIN/weiboPicDownloader)  
- [ningshu/weiboPicDownloader](https://github.com/ningshu/weiboPicDownloader) 
- [fireattack/weiboPicDownloader](https://github.com/fireattack/weiboPicDownloader)

## 使用

### 初始化

~~~bash
python -m pip install --upgrade pip requests python-dateutil pyjson5 colorama
~~~

### 命令行参数

~~~bash
python wbpic.py SINCE UID UID UID ...
~~~

- 无参数：拉取昨日0点开始，默认配置文件中用户列表
- 单条模式：`python wbpic.py #mid`
- SINCE: 
	- 数字：天数，拉取几天前（0点开始）
	- 日期：20030101
	- `''`：空字符串（需要引号）表示拉取所有微博
- UIDs：
	- 空：读取`conf/wbpic-uids.json`
	- 参数列表：多个用户ID
	- @文件名：指定`uids.json`文件
	- @目录名：图片仓库根目录，用户信息在仓库中二级子目录名上
		- 一级子目录为分类（`[]`包围）
		- 二级子目录名为用户名
		- 二级子目录名中，`#\d{10}`为用户ID，可以带多个
		- 二级子目录名中，`#xxxx`为标签，用于分类用户

### 配置文件

默认配置文件在`conf/`目录中。

#### wbpic-opts.json

默认选项，内容直接阅读。

#### wbpic-uids.json

用户ID List `[]`，每项为一个10位数字。

## 微博接口

记录接口分析

### 手机版页面

可以使用`Firefox`的[Add custom search engine](https://addons.mozilla.org/en-US/firefox/addon/add-custom-search-engine/)或类似插件实现快速微博访问。

- 全部微博页面		`https://m.weibo.cn/p/230413{uid}_-_WEIBO_SECOND_PROFILE_WEIBO&page={pageno}`
- 原创微博页面		`https://m.weibo.cn/p/230413{uid}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={bid}`

### 手机版接口（JSON）

- 全部微博	`https://m.weibo.cn/api/container/getIndex?containerid=230413{uid}_-_WEIBO_SECOND_PROFILE_WEIBO&page={pageno}`
- 原创微博	`https://m.weibo.cn/api/container/getIndex?containerid=230413{uid}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={bid}`
	- 下一页: r.data.cardlistInfo.since_id
~~~json
"card_type": 9
~~~
- 关注列表	`https://m.weibo.cn/api/container/getIndex?containerid=231093_-_selffollowed&page={pageno}`
	- -H "Cookie: SUB=" 
	- --compressed
	- r.data.cards[].card_group[].card_type = 10
	- 下一页: r.data.cardlistInfo.page
~~~json
"card_type": 11,
"itemid": "2310930026_1_ _2180540334",
"user": {
	"id": 2180540334,
	"screen_name": "呱呱子",
	"profile_url": "https://m.weibo.cn/u/2180540334?uid=2180540334&luicode=10000011&lfid=231093_-_selffollowed",
	"following": 1,
},
~~~
- 单条微博	`https://m.weibo.cn/statuses/show?id={mid}`
- 单条微博编辑历史	`https://m.weibo.cn/api/container/getIndex?containerid=231440_-_{mid}`

## 后继TODO

1. VIP图片分析
2. VIP首图403问题
3. Live Video转换成图片
4. HTTP 418反爬虫等待重试
