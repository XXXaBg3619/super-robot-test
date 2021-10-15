from __future__ import unicode_literals
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

import configparser

import urllib
import re
import random

app = Flask(__name__)


line_bot_api = LineBotApi("S1NRUscHr3pXdpnYh28UZlZmeEnmEbfX6rkSC3WHo/zSbBxUJcKgLEGtOoTlaHB7ntc/QBgAKFcwDuEvM5Kmtwhph1DdYBOeCcVB+N7Cnt9KRyrjdR6vA/+KONhX/VBvK+fqUq6yFpxsahuV3YRPQAdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("e104139d44baead65940861cbf50b707")

# 接收 LINE 的資訊
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 請 google 幫我們找圖
base = "https://www.google.com/search?"
@handler.add(MessageEvent, message=TextMessage)
def pixabay_isch(event):
    try:
        url = base + urllib.parse.urlencode({'q':event.message.text})[2:]
        headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'}
        req = urllib.request.Request(url, headers = headers)
        conn = urllib.request.urlopen(req)
        
        pattern = 'img srcset="\S*\s\w*,'
        img_list = []
        for match in re.finditer(pattern, str(conn.read())):
            img_list.append(match.group()[12:-3])
        random_img_url = img_list[random.randint(0, len(img_list)+1)]
            
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=random_img_url,
                preview_image_url=random_img_url
            )
        )
    # 如果找不到圖，就學你說話
    except:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text)
        )
if __name__ == "__main__":
    app.run()
