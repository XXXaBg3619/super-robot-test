from __future__ import unicode_literals, with_statement
import json, requests, re, urllib, contextlib, time
from urllib.parse import urlencode
from urllib.request import urlopen
from emoji import UNICODE_EMOJI
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage


app = Flask(__name__)

line_bot_api = LineBotApi("S1NRUscHr3pXdpnYh28UZlZmeEnmEbfX6rkSC3WHo/zSbBxUJcKgLEGtOoTlaHB7ntc/QBgAKFcwDuEvM5Kmtwhph1DdYBOeCcVB+N7Cnt9KRyrjdR6vA/+KONhX/VBvK+fqUq6yFpxsahuV3YRPQAdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("e104139d44baead65940861cbf50b707")


limit = 5    # 每次傳送之商品數上限


def make_tiny(url):
    request_url = "http://tinyurl.com/api-create.php?" + urlencode({"url": url})
    with contextlib.closing(urlopen(request_url)) as response:
        return response.read().decode("utf-8")
def isEmoji(content):
    for emoji in UNICODE_EMOJI['en']:
        if content.count(emoji) > 0:
            return True
    return False
def Append(s):
    for i in s:
        b = []
        for j in s[i]:
            a = j
            b += [f" {a}", f"{a} ", f" {a} "]
        s[i] += b
    return s

store_name = {
        "pchome": ["pchome", "Pchome", "PChome24h"],
        "momo": ["momo", "Momo", "MOMO"],
        "shopee": ["shopee", "Shopee"]
    }
store_name = Append(store_name)


# PChome線上購物 爬蟲
class PchomeSpider():
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36'}

    # 送出 GET 請求
    def request_get(self, url, params=None, to_json=True):
        # param url: 請求網址
        # param params: 傳遞參數資料
        # param to_json: 是否要轉為 JSON 格式
        # return data: requests 回應資料
        r = requests.get(url, params)
        print(r.url)
        if r.status_code != requests.codes.ok:
            print(f'網頁載入發生問題：{url}')
        try:
            if to_json:
                data = r.json()
            else:
                data = r.text
        except Exception as e:
            print(e)
            return None
        return data

    # 搜尋商品
    def search_products(self, keyword, max_page=1, shop='全部', sort='有貨優先', price_min=-1, price_max=-1, is_store_pickup=False, is_ipost_pickup=False):
        # param keyword: 搜尋關鍵字
        # param max_page: 抓取最大頁數
        # param shop: 賣場類別 (全部、24h購物、24h書店、廠商出貨、PChome旅遊)
        # param sort: 商品排序 (有貨優先、精準度、價錢由高至低、價錢由低至高、新上市)
        # param price_min: 篩選"最低價" (需與 price_max 同時用)
        # param price_max: 篩選"最高價" (需與 price_min 同時用)
        # param is_store_pickup: 篩選"超商取貨"
        # param is_ipost_pickup: 篩選"i 郵箱取貨"
        # return products: 搜尋結果商品
        products = []
        all_shop = {
            '全部': 'all',
            '24h購物': '24h',
            '24h書店': '24b',
            '廠商出貨': 'vdr',
            'PChome旅遊': 'tour',
        }
        all_sort = {
            '有貨優先': 'sale/dc',
            '精準度': 'rnk/dc',
            '價錢由高至低': 'prc/dc',
            '價錢由低至高': 'prc/ac',
            '新上市': 'new/dc',
        }

        url = f'https://ecshweb.pchome.com.tw/search/v3.3/{all_shop[shop]}/results'
        params = {'q': keyword, 'sort': all_sort[sort], 'page': 0}
        if price_min >= 0 and price_max >= 0:
            params['price'] = f'{price_min}-{price_max}'
        if is_store_pickup:
            params['cvs'] = 'all'   # 超商取貨
        if is_ipost_pickup:
            params['ipost'] = 'Y'   # i 郵箱取貨

        while params['page'] < max_page:
            params['page'] += 1
            data = self.request_get(url, params)
            if not data:
                print(f'請求發生錯誤：{url}{params}')
                break
            if data['totalRows'] <= 0:
                print('找不到有關的產品')
                break
            products.extend(data['prods'])
            if data['totalPage'] <= params['page']:
                break
        return products

def pchome(name, page = 1):
    try:
        with open("pchome_porducts_info.json") as file:
            print("存在商品搜尋紀錄")
            products = json.load(file)
    except:
        products = []
    if page == 1:
        products = PchomeSpider().search_products(name)
    elif len(products) < page * limit:
        print("爬出下20筆商品資訊")
        products = PchomeSpider().search_products(name, (page*limit)//20+1)
    with open("pchome_porducts_info.json", "w") as file:
        json.dump(products, file)
    message = ""
    print("len(products):", len(products))
    for i in range(limit*(page-1), limit*page):
        message += "https://24h.pchome.com.tw/prod/" + products[i]["Id"] + "\n"
        message += products[i]["name"] + "\n"
        message += "$" + str(products[i]["price"]) + "\n"
    message += " " * 20 + f"[第{page}頁]"
    return message

# MOMO線上購物 爬蟲
def momo_search(keyword, pages = 1):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}
    urls = []
    amount = 20 // limit
    page = pages // amount + 1
    pages = pages % amount if pages % amount != 0 else 4
    if pages != 1:
        with open("urls_momo.json") as file:
            urls = json.load(file)
    else:
        url = 'https://m.momoshop.com.tw/search.momo?_advFirst=N&_advCp=N&curPage={}&searchType=1&cateLevel=2&ent=k&searchKeyword={}&_advThreeHours=N&_isFuzzy=0&_imgSH=fourCardType'.format(page, keyword)
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, features="html.parser")
            for item in soup.select('li.goodsItemLi > a'):
                urls.append('https://m.momoshop.com.tw'+item['href'])
        with open("urls_momo.json", "w") as file:
            json.dump(urls, file)
    products = []
    urls = urls[limit*(pages-1):limit*pages]
    for i, url in enumerate(urls):
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, features="html.parser")
        name = soup.find('meta',{'property':'og:title'})['content']
        try:
            price = soup.find('meta',{'property':'product:price:amount'})['content']
        except:
            price = re.sub(r'\r\n| ','',soup.find('del').text)
        products.append({
            "link": url, 
            "name": name, 
            "price": price
            })
    with open("products_info_momo.json", "w") as file:
        json.dump(products, file)
    return products
    
def momo(name, pages = 1):
    try:
        with open("products_info_momo.json") as file:
            products = json.load(file)
    except:
        products = []
    if pages == 1:
        products = momo_search(name)
    else:
        products += momo_search(name, pages)
    with open("products_info_momo.json", "w") as file:
        json.dump(products, file)
    message = ""
    for i in range(limit*(pages-1), limit*pages):
        message += products[i]["link"] + "\n"
        message += products[i]["name"] + "\n"
        message += "$" + products[i]["price"] + "\n"
    message += " " * 20 + f"[第{pages}頁]"
    return message


# Shopee線上購物 爬蟲
def shopee_search(name, page = 1):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36 Edg/88.0.705.68',
        'x-api-source': 'pc',
        'referer': f'https://shopee.tw/search?keyword={urllib.parse.quote(name)}'
    }
    url = f'https://shopee.tw/api/v2/search_items/?by=relevancy&keyword={name}&limit=50&newest={50*(page-1)}&order=desc&page_type=search&version=2'
    resq = requests.Session().get(url, headers=headers)
    if resq.status_code == requests.codes.ok:
        data = resq.json()
    products = []
    for item in data["items"]:
        title = item["name"]
        shopid, itemid = item["shopid"], item["itemid"]
        if isEmoji(title) == True:
            link = make_tiny(f"https://shopee.tw/{title}-i.{shopid}.{itemid}")
            make_tiny = True
        else:
            for i in ("[", "]", "<", ">"):
                if i in title:
                    link = make_tiny(f"https://shopee.tw/{title}-i.{shopid}.{itemid}")
                    make_tiny = True
                    break
                make_tiny = False
        if not make_tiny:
            title_fix = title.replace(" ", "-")
            link = f"https://shopee.tw/{title_fix}-i.{shopid}.{itemid}"
        price_min, price_max = int(item["price_min"])//100000, int(item["price_max"])//100000
        if price_min == price_max:
            price = str(int(item["price"]) // 100000)
        else:
            price = f"{price_min} ~ {price_max}"
        products.append({"link": link, "name": title, "price": price})
    return products

def shopee(name, page = 1):
    try:
        with open("products_info_shopee.json") as file:
            products = json.load(file)
    except:
        products = []
    if page == 1:
        products = shopee_search(name)
    else:
        pages = page // (50 // limit) + 1
        products += shopee_search(name, pages)
    with open("products_info_shopee.json", "w") as file:
        json.dump(products, file)
    message = ""
    for i in range(limit*(page-1), limit*page):
        message += products[i]["link"] + "\n"
        message += products[i]["name"] + "\n"
        message += "$" + products[i]["price"] + "\n"
    message += " " * 20 + f"[第{page}頁]"
    return message

    
    

# 接收 LINE 的資訊
@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 搜尋商品
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    start = time.time()
    message = ""
    text = event.message.text
    info = {}
    if ";" in text:
        info["search_name"], info["platform"] = text.split(";")
        print("info:", info)
        if info["platform"] in store_name["pchome"]:
            print("Search on PChome")
            message = pchome(info["search_name"])
        elif info["platform"] in store_name["momo"]:
            print("Search on MOMO")
            message = momo(info["search_name"])
        elif info["platform"] in store_name["shopee"]:
            message = shopee(info["search_name"])
        with open("search_info.json", "w") as file:
                json.dump(info, file)
    elif text.isdigit() == True:
        with open("search_info.json") as file:
            info = json.load(file)
        if info["platform"] == "pchome":
            message = pchome(info["search_name"], int(text))
        elif info["platform"] == "momo":
            message = momo(info["search_name"], int(text))
        elif info["platform"] == "shopee":
            message = shopee(info["search_name"], int(text))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text = message))
    end = time.time()
    print("time:", end - start, "s")

if __name__ == "__main__":
    app.run()
