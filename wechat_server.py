import hashlib
import os
import time
import xml.etree.ElementTree as ET

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response

from main import chat


WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "xiaoxiaoyi_token")

app = FastAPI(title="XiaoXiaoYi WeChat Server")
wechat_histories = {}


def check_signature(signature, timestamp, nonce):
    items = [WECHAT_TOKEN, timestamp, nonce]
    items.sort()
    raw = "".join(items).encode("utf-8")
    return hashlib.sha1(raw).hexdigest() == signature


def parse_wechat_message(xml_text):
    root = ET.fromstring(xml_text)
    data = {child.tag: child.text or "" for child in root}
    return data


def build_text_reply(to_user, from_user, content):
    now = int(time.time())
    safe_content = content.replace("]]>", "]]]]><![CDATA[>")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{now}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{safe_content}]]></Content>
</xml>"""


def get_history(openid):
    return wechat_histories.setdefault(openid, [])


def save_history(openid, user_text, assistant_text):
    history = get_history(openid)
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": assistant_text})
    del history[:-12]


@app.get("/wechat")
async def verify_wechat(
    signature: str = "",
    timestamp: str = "",
    nonce: str = "",
    echostr: str = "",
):
    if check_signature(signature, timestamp, nonce):
        return PlainTextResponse(echostr)
    return PlainTextResponse("signature error", status_code=403)


@app.post("/wechat")
async def receive_wechat_message(request: Request):
    body = await request.body()
    xml_text = body.decode("utf-8")
    message = parse_wechat_message(xml_text)

    from_user = message.get("FromUserName", "")
    to_user = message.get("ToUserName", "")
    msg_type = message.get("MsgType", "")

    if msg_type != "text":
        reply = "小小易目前只支持文字消息。你可以发送订单号或售后问题，例如：订单 EC20260702002 物流到哪了？"
        return Response(
            content=build_text_reply(from_user, to_user, reply),
            media_type="application/xml; charset=utf-8",
        )

    user_text = message.get("Content", "").strip()
    if not user_text:
        reply = "请发送订单号或售后问题，小小易会帮你处理。"
    else:
        try:
            reply = chat(user_text, get_history(from_user))
        except Exception:
            reply = "小小易暂时处理失败，请稍后再试，或换一种说法描述你的售后问题。"

    save_history(from_user, user_text, reply)
    return Response(
        content=build_text_reply(from_user, to_user, reply),
        media_type="application/xml; charset=utf-8",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
