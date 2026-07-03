# 接入微信公众号测试号

本文档说明如何把当前“小小易”售后智能客服接入微信公众号测试号。

## 1. 打开微信公众号测试号

测试号入口：

```text
https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login
```

用微信扫码登录后，找到“接口配置信息”。

## 2. 启动微信接口服务

在项目目录运行：

```shell
cd /d D:\customer-chatbot-demo-agent-rag-langchain
$env:WECHAT_TOKEN="xiaoxiaoyi_token"
.conda\python.exe wechat_server.py
```

服务默认监听：

```text
http://127.0.0.1:8000/wechat
```

## 3. 准备公网访问地址

微信服务器无法访问本机的 `127.0.0.1`，需要使用内网穿透工具把本地 8000 端口暴露到公网。

可以使用：

- cpolar
- ngrok
- 花生壳
- Cloudflare Tunnel

假设内网穿透得到的公网地址是：

```text
https://example-tunnel.com
```

那么微信公众号测试号后台要填写：

```text
URL: https://example-tunnel.com/wechat
Token: xiaoxiaoyi_token
```

Token 必须和启动服务时的 `WECHAT_TOKEN` 一致。

## 4. 验证并启用

在测试号后台点击“提交”。如果验证通过，微信会启用该接口。

然后扫描测试号二维码关注公众号，在微信里发送：

```text
订单 EC20260702002 物流到哪了？
```

小小易应该会回复订单物流信息。

## 5. 当前支持

微信公众号接口当前支持：

- 文本消息
- 订单查询
- 物流查询
- 退款
- 退货退款
- 换货
- 补发
- 破损少件
- 发票咨询
- 简单日常聊天

暂不支持：

- 图片凭证上传识别
- 菜单按钮
- 主动客服消息
- 真正人工客服接入
- 多进程/数据库持久化聊天记录

## 6. 注意事项

微信公众号被动回复有时间限制。当前项目的高频售后问题会快速回复；如果问题需要调用本地大模型，可能比规则回复慢。

真实上线建议改成：

```text
先快速回复“已收到，正在查询”
再通过客服消息接口补发完整结果
```
