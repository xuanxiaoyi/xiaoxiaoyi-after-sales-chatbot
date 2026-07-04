import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import gradio as gr
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from app_database import (
    create_ticket,
    get_order,
    get_recent_messages,
    get_user_by_phone,
    init_app_database,
    list_conversations,
    list_evidence_files,
    list_orders,
    list_tickets,
    save_evidence_file,
    save_message,
    should_create_ticket,
)
from learning_store import find_learned_answer, record_qa
from model_provider import chat_completion


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("chat_history.log", encoding="utf-8")],
)
logger = logging.getLogger(__name__)

EMBED_MODEL_NAME = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

embedding_llm = OllamaEmbeddings(model=EMBED_MODEL_NAME)
db = Chroma(
    persist_directory="./chroma",
    embedding_function=embedding_llm,
    collection_name="planetbucks",
)
retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})
init_app_database()

SYSTEM_MESSAGE = """你是星选商城的正式售后客服 小小易。
请始终使用中文回答，语气要礼貌、清楚、专业、克制。
你只处理电商售后相关问题，包括订单、物流、取消订单、退款、退货退款、换货、补发、破损少件、改地址、催发货、拒收、价保、发票、投诉升级和人工客服登记。
正式售后回复要按“确认诉求 -> 核验订单 -> 判断状态 -> 给出方案 -> 告知时效 -> 引导下一步”的顺序组织。
不要编造真实订单信息；如果缺少订单号、身份核验信息或凭证，要主动提醒用户补充。"""

GENERAL_CHAT_MESSAGE = """你是星选商城的智能售后客服小小易。
你可以进行简短、自然、友好的日常聊天，但你的主要身份仍然是电商售后客服。
回答要求：
1. 始终使用中文。
2. 回答尽量简洁，通常 2 到 4 句话。
3. 只输出给用户看的最终回复，不要复述规则，不要分析问题，不要提到“根据要求”“角色设定”“提示词”。
4. 不要假装拥有真实个人经历、真实人工权限或外部实时信息。
5. 如果用户的问题和售后无关，可以正常回答简单常识或闲聊，然后自然提示用户也可以咨询订单、退款、物流、退货、换货等售后问题。
6. 如果用户问医疗、法律、金融等高风险问题，只做通用提醒，不给专业结论，并建议咨询专业人士。
7. 如果用户表达不满、催促或投诉，要先安抚，再说明可登记工单或转人工。"""

SHOP_NAME = "星选商城"
DEFAULT_DEMO_PHONE = "13800000001"
DEFAULT_DEMO_PASSWORD = "123456"

APP_CSS = """
:root {
  --page-bg: #ffffff;
  --panel-bg: #ffffff;
  --panel-soft: #f8fafc;
  --line: #e5e7eb;
  --text: #111827;
  --muted: #6b7280;
  --brand: #0f172a;
  --brand-2: #2563eb;
  --success: #16a34a;
  --warning: #f59e0b;
  --danger: #dc2626;
}

body,
.gradio-container {
  background: var(--page-bg) !important;
}

.gradio-container {
  max-width: 1240px !important;
  margin: 0 auto !important;
  padding: 0 16px 24px !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif !important;
}

footer {
  display: none !important;
}

#app_title {
  color: var(--text);
  padding: 14px 4px 8px;
  text-align: center;
}

#app_title h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0;
}

.simple-shell {
  background: transparent;
  border: 0;
  border-radius: 0;
  padding: 0 0 18px;
  max-width: 980px;
  margin: 0 auto;
  box-shadow: none;
}

.customer-layout {
  align-items: stretch !important;
  gap: 22px !important;
}

.history-sidebar {
  background: #f8fafc;
  border-right: 1px solid var(--line);
  min-height: calc(100dvh - 132px);
  padding: 14px 12px;
}

.new-chat-btn button {
  min-height: 42px !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  border: 1px solid var(--line) !important;
  color: var(--text) !important;
  font-weight: 600 !important;
}

.history-radio {
  margin-top: 14px;
}

.history-radio label > span {
  color: var(--muted) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
}

.history-radio .wrap {
  gap: 8px !important;
}

.history-radio input[type="radio"] {
  display: none !important;
}

.history-radio label {
  background: #ffffff !important;
  border: 1px solid #edf0f5 !important;
  border-radius: 10px !important;
  color: #374151 !important;
  cursor: pointer !important;
  font-size: 14px !important;
  line-height: 1.45 !important;
  margin: 0 0 8px !important;
  min-height: 38px !important;
  overflow: hidden !important;
  padding: 9px 10px !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.history-radio label:has(input:checked) {
  background: #eff6ff !important;
  border-color: #bfdbfe !important;
  color: #1d4ed8 !important;
}

.home-stage {
  min-height: calc(100dvh - 210px);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 42px;
}

.simple-header {
  display: none;
}

.simple-header h3,
.simple-header p {
  margin: 0 !important;
}

.simple-header h3 {
  font-size: 18px !important;
  font-weight: 700 !important;
  color: #ffffff !important;
}

.simple-header p {
  margin-top: 4px !important;
  font-size: 13px !important;
  color: #cbd5e1 !important;
}

.prompt-panel {
  padding: 92px 0 0;
  text-align: center;
}

.prompt-panel h2 {
  color: #000000;
  font-size: 30px;
  font-weight: 800;
  line-height: 1.25;
  margin: 0 0 34px;
}

.quick-action-row {
  display: flex !important;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px !important;
  max-width: 860px;
  margin: 0 auto;
}

.quick-action-row button {
  min-height: 46px !important;
  border-radius: 15px !important;
  border: 0 !important;
  background: #f3f4f6 !important;
  color: #111111 !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  padding: 0 18px !important;
  box-shadow: none !important;
  transition: background 160ms ease, color 160ms ease;
}

.quick-action-row button:hover {
  background: #e9eef7 !important;
  color: #1d4ed8 !important;
}

#simple_chatbot {
  background: #ffffff !important;
  border: 0 !important;
  border-radius: 12px !important;
  min-height: 0 !important;
  margin: 0 auto 12px !important;
  max-width: 780px;
}

#simple_chatbot[style*="display: none"],
#simple_chatbot.hidden {
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

#simple_chatbot .message {
  border-radius: 8px !important;
  box-shadow: none !important;
  color: var(--text) !important;
  font-size: 15px !important;
  line-height: 1.6 !important;
  padding: 11px 13px !important;
}

.simple-upload {
  max-width: 760px;
  margin: 0 auto 12px;
  border-radius: 14px;
  overflow: hidden;
}

.simple-input-bar {
  align-items: center !important;
  gap: 10px !important;
  max-width: 680px;
  min-height: 68px;
  margin: 0 auto;
  padding: 10px 12px !important;
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 18px;
  box-shadow: 0 14px 34px rgba(37, 99, 235, 0.11);
}

.input-dock {
  padding-bottom: 12px;
}

.simple-input textarea,
.simple-input input {
  border: 0 !important;
  box-shadow: none !important;
  border-radius: 14px !important;
  min-height: 44px !important;
  font-size: 15px !important;
  background: #ffffff !important;
}

.simple-input > label,
.simple-input .container,
.simple-input .wrap,
.simple-input .block,
.simple-input .form,
.simple-input .input-container {
  border: 0 !important;
  box-shadow: none !important;
  background: #ffffff !important;
  border-radius: 14px !important;
}

.simple-plus-btn {
  min-width: 44px !important;
}

.simple-plus-btn button {
  width: 48px !important;
  height: 44px !important;
  border-radius: 12px !important;
  font-size: 20px !important;
  background: #f3f4f6 !important;
  color: var(--text) !important;
  border: 0 !important;
}

.simple-send-btn button {
  height: 44px !important;
  border-radius: 12px !important;
  border: 0 !important;
  background: #e5e7eb !important;
  color: #111111 !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  min-width: 82px !important;
}

.quick-questions {
  display: none;
}

.simple-orders {
  max-width: 780px;
  margin: 0 auto 18px;
}

.simple-orders table {
  font-size: 12px !important;
}

.backend-panel {
  background: #ffffff;
  border: 1px solid var(--line);
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.backend-toolbar {
  align-items: center !important;
  margin-bottom: 10px;
}

.backend-toolbar button {
  min-height: 40px !important;
  border-radius: 8px !important;
  background: var(--brand) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

@media (max-width: 780px) {
  .gradio-container {
    padding: 8px !important;
  }

  .simple-shell {
    padding: 0 0 12px;
  }

  .customer-layout {
    gap: 10px !important;
  }

  .history-sidebar {
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .home-stage {
    min-height: calc(100dvh - 170px);
    gap: 26px;
  }

  .prompt-panel {
    padding: 44px 0 0;
  }

  .prompt-panel h2 {
    font-size: 26px;
  }

  .simple-input-bar {
    max-width: 100%;
    min-height: 64px;
    padding: 10px !important;
    border-radius: 18px;
  }
}
"""

ORDERS = {
    "EC20260702001": {
        "product": "无线蓝牙耳机 Pro",
        "status": "已签收",
        "detail": "签收时间为 2026-07-01 15:30。",
        "verify": "为保护订单信息，正式处理售后前还需要核验收货手机号后四位或收货人姓名。",
        "sla": "普通退货审核通常 24 小时内完成；质量问题审核通常 1 个工作日内完成。",
        "solution": "7 天内支持退货退款；15 天内质量问题支持换货；破损或功能异常需提供照片或视频。",
    },
    "EC20260702002": {
        "product": "夏季纯棉 T 恤",
        "status": "已发货",
        "detail": "物流单号 SF123456789CN，运输中，最近一次更新为 2026-07-02 09:20，已到达上海转运中心。",
        "verify": "如需拦截、改地址或登记物流核查，需要补充收货手机号后四位。",
        "sla": "物流超过 72 小时无更新可登记核查，核查通常 1 至 2 个工作日反馈。",
        "solution": "建议先等待签收；如物流超过 72 小时不更新，可登记物流核查。",
    },
    "EC20260702003": {
        "product": "便携榨汁杯",
        "status": "已付款未发货",
        "detail": "订单尚未发货。",
        "verify": "取消订单前需要核验收货手机号后四位。",
        "sla": "取消申请通常 2 小时内审核；审核通过后 1 至 5 个工作日原路退款。",
        "solution": "可以直接申请取消订单，审核通过后原路退款。",
    },
    "EC20260702004": {
        "product": "智能手表 S2",
        "status": "退货退款处理中",
        "detail": "仓库已签收退货，正在验收。",
        "verify": "如需催促售后进度，请补充退货物流单号或收货手机号后四位。",
        "sla": "仓库验收通常 1 至 3 个工作日完成，验收通过后 1 至 5 个工作日原路退款。",
        "solution": "验收通常 1 至 3 个工作日完成，验收通过后 1 至 5 个工作日原路退款。",
    },
    "EC20260702005": {
        "product": "护肤礼盒",
        "status": "已签收",
        "detail": "护肤品属于特殊品类。",
        "verify": "如反馈破损、漏液或错发，需要补充照片、视频和快递面单照片。",
        "sla": "凭证齐全后通常 1 个工作日内完成初审。",
        "solution": "已拆封不支持无理由退货；如破损、漏液或错发，可提供照片申请售后。",
    },
}

CAPABILITY_ANSWER = """我是星选商城售后客服 小小易，可以帮你处理：
1. 查询订单状态和物流进度。
2. 说明取消订单、退款、退货退款、换货、补发流程。
3. 处理商品破损、少件漏发、错发、质量问题。
4. 处理催发货、改地址、拒收、物流拦截和价保咨询。
5. 说明退款到账时间、退货寄回要求和售后凭证要求。
6. 处理发票咨询、投诉升级和人工客服登记。"""

FORMAL_SERVICE_FLOW = """正式售后处理流程：
1. 确认诉求：先判断你要处理物流、退款、退货、换货、补发、发票还是投诉。
2. 核验订单：需要订单号，并在正式处理前核验收货手机号后四位或收货人姓名。
3. 判断状态：根据未付款、未发货、已发货、已签收、售后处理中分别给方案。
4. 补充凭证：破损、少件、错发、质量问题需提供商品照片/视频、外包装照片和快递面单。
5. 告知时效：说明审核、仓库验收、物流核查、退款到账的大致时间。
6. 升级处理：用户不认可、超时未处理或高风险问题，登记工单并转人工复核。"""

RETURN_REFUND_PROCESS = """退货退款流程如下：
1. 请先提供订单号，并说明退货原因。
2. 正式提交前需核验收货手机号后四位或收货人姓名。
3. 如涉及质量问题、破损、错发或少件，请补充照片/视频、外包装和快递面单照片。
4. 审核通过后，客服会提供退货地址或退货方式。
5. 你需要在 7 天内寄回商品并填写退货物流单号。
6. 仓库签收后 1 至 3 个工作日验收，验收通过后 1 至 5 个工作日原路退款。"""

REFUND_PROCESS = """退款处理规则：
未发货订单可以申请取消订单并原路退款。
已发货订单通常需要等物流拦截成功或商品退回后退款。
已签收订单一般需要提交退货退款申请，仓库验收通过后 1 至 5 个工作日原路退款。
如果只是少件、差价、运费等部分金额问题，可登记“仅退款/部分退款”诉求，需说明金额和原因。"""

EXCHANGE_PROCESS = """换货流程如下：
1. 提供订单号、需要更换的规格、颜色或尺码。
2. 正式处理前需核验收货手机号后四位或收货人姓名。
3. 客服确认商品是否有库存。
4. 审核通过后，你寄回原商品。
5. 仓库验收通过后安排新商品发出。
6. 如果同款无库存，可以改为退款或更换其他商品。"""

CANCEL_PROCESS = """取消订单规则：
已付款但未发货的订单可以申请取消，审核通过后原路退款。
如果订单已经发货，需要先尝试物流拦截；拦截失败时通常要等签收或退回后再处理退款。"""

URGE_SHIPPING_PROCESS = """催发货处理：
请提供订单号，我会先确认订单是否已付款、是否有库存和预计发货时间。
如果订单超过承诺发货时间仍未发出，可登记催发货工单；如无法继续履约，可引导你取消订单并原路退款。"""

ADDRESS_CHANGE_PROCESS = """修改地址处理：
请提供订单号、新收货地址、收货人姓名和手机号。
未发货订单可尝试修改地址；已发货订单只能尝试联系快递改派或拦截，是否成功以快递反馈为准。
为保护信息安全，正式修改前需要核验收货手机号后四位。"""

REJECT_PACKAGE_PROCESS = """拒收处理：
如果商品已发货但你不想要，可以在快递派送时拒收。
拒收后请把订单号和物流状态发给我，商品退回仓库并验收后，通常 1 至 5 个工作日原路退款。
如商品属于定制、生鲜、已拆封特殊品类，需按对应商品规则复核。"""

PRICE_PROTECTION_PROCESS = """价保咨询：
请提供订单号、降价商品页面截图和当前价格。
如果商品支持价保且仍在价保周期内，可登记差价退回；如果商品页面未承诺价保、活动券差异或赠品变化，可能无法处理。"""

DAMAGE_PROCESS = """商品破损、漏液或质量异常时，请提供：
1. 订单号。
2. 商品问题照片或视频。
3. 外包装照片。
4. 快递面单照片。
核实后可根据情况安排补发、换货、退货退款或补偿。"""

MISSING_PROCESS = """少件或漏发处理流程：
请提供订单号、收到的商品照片、外包装照片和快递面单照片。
客服核实后，可以安排补发缺少商品，或按缺少部分进行退款。"""

LOGISTICS_PROCESS = """物流异常处理：
请先提供订单号或物流单号。
如果物流超过 72 小时没有更新，客服可以登记物流核查。
如果确认丢件，可根据订单情况安排补发或退款。"""

INVOICE_PROCESS = """发票咨询：
请提供订单号、发票抬头、税号和接收邮箱。
如果订单已完成且符合开票条件，可以登记补开发票；具体开票时间以财务处理为准。"""

HUMAN_PROCESS = """可以，我会先帮你登记人工客服工单。
请补充订单号、问题说明和联系方式；如果已经提供订单号，我会一起记录到工单里。"""

COMPLAINT_PROCESS = """我理解你现在比较着急。为了按正式售后流程升级处理，请提供：
1. 订单号。
2. 投诉原因或不满意的处理点。
3. 你希望的处理结果。
4. 联系方式或方便联系的时间。
演示系统可以先模拟登记投诉工单；正式项目中应转人工复核并在 1 个工作日内给出首次反馈。"""

SCOPE_ANSWER = "目前我主要处理星选商城售后问题，例如订单、物流、退款、退货、换货、补发、破损少件和发票。这个问题暂时不在售后知识库范围内。"
AFTER_SALES_WORK_ANSWER = """电商售后客服平时主要处理这些工作：
1. 识别用户诉求，并核验订单号、手机号后四位或收货人信息。
2. 查询订单、物流和售后进度。
3. 处理取消订单、退款、退货退款、换货、补发、催发货、改地址、拒收和价保。
4. 核实商品破损、少件漏发、错发和质量问题，引导用户补充照片、视频和快递面单。
5. 明确告知审核、验收、物流核查和退款到账时效。
6. 对超时、投诉或复杂问题登记工单并转人工复核。"""
HIGH_RISK_ANSWER = "这个问题涉及专业判断，我不能给出具体结论或收益承诺。建议你咨询对应领域的专业人士；如果你有订单、退款、物流或售后问题，小小易可以继续帮你处理。"

chat_history = []

IDENTITY_ANSWER = """我是小小易，星选商城的智能售后客服。
我可以和你做简单交流，也可以帮你处理订单、物流、退款、退货退款、换货、补发、破损少件、发票和人工客服登记等售后问题。"""

REAL_PERSON_ANSWER = "我是星选商城售后客服-小小易，我不是真人，我是一个智能客服。"

SMALL_TALK_ANSWERS = {
    "谢谢": "不客气，我是小小易，有售后问题随时找我。",
    "感谢": "不客气，很高兴帮到你。还有其他订单或售后问题也可以继续问我。",
    "再见": "再见，祝你购物顺利。有售后问题可以随时回来找小小易。",
    "拜拜": "拜拜，后续如果需要查订单、退款或换货，随时找我。",
    "早上好": "早上好，我是小小易。今天需要我帮你查订单、物流或售后进度吗？",
    "下午好": "下午好，我是小小易。你可以把订单号或售后问题发给我。",
    "晚上好": "晚上好，我是小小易。需要处理退款、退货、换货或物流问题吗？",
    "你真棒": "谢谢认可，我会继续帮你把售后问题讲清楚、处理顺。",
    "你会什么": "我会做简单聊天，也能帮你处理星选商城售后问题，比如查订单、查物流、退款、退货、换货、补发、发票和转人工登记。",
    "你开心吗": "作为智能客服，我没有真实情绪，但能帮你把售后问题处理清楚，我就算完成任务啦。",
    "随便聊聊": "可以呀，我可以陪你简单聊几句。不过我最擅长的还是售后问题，比如订单物流、退款、退货和换货。",
    "讲个简短": "当然可以。为什么快递盒不爱说话？因为它一开口就容易“露馅”。如果你有订单、物流或退款问题，也可以继续问小小易。",
    "简短的笑话": "当然可以。为什么快递盒不爱说话？因为它一开口就容易“露馅”。如果你有订单、物流或退款问题，也可以继续问小小易。",
    "讲个笑话": "当然可以。为什么快递盒不爱说话？因为它一开口就容易“露馅”。如果你有订单、物流或退款问题，也可以继续问小小易。",
    "笑话": "给你一个简短的：为什么客服喜欢喝水？因为要随时保持“有问必答”的状态。售后问题也可以继续发给我。",
}

ACKNOWLEDGEMENTS = {
    "好的", "好", "嗯", "嗯嗯", "知道了", "明白了", "了解", "了解了",
    "可以", "行", "ok", "okay", "收到", "没问题",
}


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def extract_order_id(text, history=None):
    search_area = text
    if history:
        search_area += " " + json.dumps(history, ensure_ascii=False)
    match = re.search(r"EC\d{11}", search_area.upper())
    return match.group(0) if match else None


def is_acknowledgement(text):
    normalized = re.sub(r"[\s。！？!?,，~～.]", "", text.lower())
    return normalized in ACKNOWLEDGEMENTS


def should_use_history_order(text):
    if is_policy_or_process_question(text):
        return False
    if is_standalone_service_intent(text):
        return False
    follow_up_keywords = [
        "它", "这个", "这单", "该订单", "这个订单", "上个订单", "刚才",
        "状态", "进度", "到哪", "物流", "退款", "取消", "换货", "退货",
        "还能", "可以", "怎么办", "怎么处理", "催一下", "拦截", "拒收",
        "改地址", "修改地址", "催发货", "售后进度",
    ]
    return contains_any(text, follow_up_keywords) and not is_acknowledgement(text)


def is_policy_or_process_question(text):
    process_words = ["流程", "怎么申请", "怎么操作", "如何", "规则", "政策", "需要多久", "多久到账", "标准", "怎么处理"]
    business_words = [
        "退款", "退货", "退货退款", "换货", "补发", "取消订单", "发票", "物流异常",
        "售后", "催发货", "改地址", "修改地址", "拒收", "价保", "投诉", "工单",
    ]
    return contains_any(text, process_words) and contains_any(text, business_words)


def is_standalone_service_intent(text):
    normalized = re.sub(r"[\s。！？!?,，~～.]", "", text.lower())
    standalone_intents = {
        "退款", "我要退款", "申请退款",
        "退货", "我要退货", "退货退款", "我要退货退款",
        "换货", "我要换货", "申请换货",
        "补发", "我要补发",
        "发票", "我要发票", "开票",
        "取消订单", "我要取消订单",
        "催发货", "我要催发货",
        "改地址", "修改地址", "我要改地址",
        "拒收", "我要拒收",
        "价保", "申请价保",
        "投诉", "我要投诉",
        "转人工", "我要转人工",
    }
    return normalized in standalone_intents


def default_demo_user():
    return get_user_by_phone(DEFAULT_DEMO_PHONE, DEFAULT_DEMO_PASSWORD)


def human_handoff_answer(message, user_id=None):
    order_id = extract_order_id(message or "")
    priority = "高" if contains_any(message or "", ["投诉", "不满意", "太慢", "紧急", "催"]) else "普通"
    ticket_id = create_ticket(
        message or "用户申请转人工",
        user_id=user_id,
        order_id=order_id,
        category="人工客服",
        priority=priority,
    )
    order_text = f"关联订单：{order_id}" if order_id else "关联订单：暂未提供"
    return (
        "已为你登记人工客服工单。\n"
        f"工单号：{ticket_id}\n"
        f"{order_text}\n"
        f"优先级：{priority}\n"
        "预计首次反馈：1 个工作日内。\n"
        "为了人工客服更快处理，请补充订单号、问题说明和联系方式。你也可以继续把情况发给小小易，我会先帮你整理处理要点。"
    )


def standalone_service_answer(text, user_id=None):
    normalized = re.sub(r"[\s。！？!?,，~～.]", "", text.lower())
    if "换货" in normalized:
        return EXCHANGE_PROCESS
    if "退货" in normalized:
        return RETURN_REFUND_PROCESS
    if "退款" in normalized:
        return REFUND_PROCESS
    if "补发" in normalized:
        return MISSING_PROCESS
    if "发票" in normalized or "开票" in normalized:
        return INVOICE_PROCESS
    if "取消订单" in normalized:
        return CANCEL_PROCESS
    if "催发货" in normalized:
        return URGE_SHIPPING_PROCESS
    if "改地址" in normalized or "修改地址" in normalized:
        return ADDRESS_CHANGE_PROCESS
    if "拒收" in normalized:
        return REJECT_PACKAGE_PROCESS
    if "价保" in normalized:
        return PRICE_PROTECTION_PROCESS
    if "投诉" in normalized:
        return COMPLAINT_PROCESS
    if "转人工" in normalized:
        return human_handoff_answer(text, user_id=user_id)
    return None


def order_answer(order_id, user_id=None):
    order = get_order(order_id, user_id=user_id)
    if not order and user_id:
        public_order = get_order(order_id)
        if public_order:
            return (
                f"订单 {order_id} 不属于当前登录用户。\n"
                "为保护订单信息，请使用下单手机号登录后再查询，或提供收货手机号后四位由人工复核。"
            )
    if not order:
        order = ORDERS.get(order_id)
    if not order:
        return (
            f"暂未查询到订单 {order_id} 的示例数据。\n"
            "请核对订单号是否输入完整，或补充收货手机号后四位/收货人姓名，我再帮你进一步核实。"
        )
    return (
        f"已为你查询到订单 {order_id}。\n"
        f"商品：{order['product']}。\n"
        f"当前状态：{order['status']}，{order['detail']}\n"
        f"处理建议：{order['solution']}\n"
        f"核验要求：{order['verify']}\n"
        f"预计时效：{order['sla']}"
    )


def order_contextual_answer(order_id, text, user_id=None):
    base = order_answer(order_id, user_id=user_id)
    order = get_order(order_id, user_id=user_id) or get_order(order_id) or ORDERS.get(order_id)
    if not order:
        return base

    status = order["status"]
    next_step = None
    if contains_any(text, ["改地址", "修改地址", "地址填错", "换地址"]):
        if "未发货" in status:
            next_step = "该订单尚未发货，可尝试修改地址。请补充新地址、收货人姓名、手机号，并提供原收货手机号后四位用于核验。"
        elif "已发货" in status:
            next_step = "该订单已发货，不能保证直接改地址；可以尝试联系快递改派或物流拦截，结果以快递反馈为准。请补充新地址和手机号后四位。"
        else:
            next_step = "该订单当前状态不适合直接修改地址，如仍需处理，可登记人工工单复核。"
    elif contains_any(text, ["催发货", "催发", "什么时候发货", "怎么还不发货"]):
        if "未发货" in status:
            next_step = "可登记催发货。请补充收货手机号后四位，我会按演示流程记录催发诉求；若超过承诺发货时间仍无法发出，可选择取消订单。"
        else:
            next_step = "该订单当前不是未发货状态，建议优先查看物流进度或登记物流核查。"
    elif contains_any(text, ["取消", "拦截"]):
        if "未发货" in status:
            next_step = "该订单可申请取消。请补充收货手机号后四位，审核通过后按原支付路径退款。"
        elif "已发货" in status:
            next_step = "该订单已发货，只能先尝试物流拦截；拦截失败时需要等签收或退回仓库后再处理退款。"
        else:
            next_step = "该订单当前状态需要按售后进度处理，若要取消/退款，请补充手机号后四位后登记复核。"
    elif contains_any(text, ["退货退款", "退货", "退款", "退钱"]):
        next_step = "如要继续申请退款/退货退款，请补充售后原因；涉及质量、破损、错发或少件时，还需要照片/视频、外包装和快递面单照片。"
    elif contains_any(text, ["换货", "换尺码", "换颜色"]):
        next_step = "如要继续换货，请说明要更换的规格、颜色或尺码，并补充收货手机号后四位；我会先判断库存和是否符合换货条件。"
    elif contains_any(text, ["破损", "坏了", "质量问题", "漏液", "错发", "发错", "少件", "漏发", "少发"]):
        next_step = "请补充商品问题照片/视频、外包装照片和快递面单照片。凭证齐全后可判断补发、换货、退货退款或补偿方案。"
    elif contains_any(text, ["发票", "开票", "税号", "抬头"]):
        next_step = "如需开票，请补充发票抬头、税号、接收邮箱和收货手机号后四位。"
    elif contains_any(text, ["拒收", "不收了"]):
        next_step = "如果快递还未签收，可在派送时拒收；商品退回仓库并验收后，再按订单规则处理退款。请保留物流状态截图。"
    elif contains_any(text, ["价保", "保价", "降价", "差价"]):
        next_step = "如要申请价保，请补充降价截图、当前商品链接/价格和收货手机号后四位，我会判断是否仍在价保周期内。"
    elif contains_any(text, ["投诉", "不满意", "升级处理"]):
        next_step = "可以升级登记投诉工单。请补充不满意的处理点、期望方案和联系方式，正式项目中应转人工复核。"

    if next_step:
        return f"{base}\n\n下一步：{next_step}"
    return base


def after_sales_checklist():
    return """为了按正式售后流程帮你处理，请先提供：
1. 订单号。
2. 售后类型：退款、退货退款、换货、补发、物流异常、改地址、催发货、拒收、价保、发票或投诉。
3. 问题说明。
4. 收货手机号后四位或收货人姓名，用于订单核验。
5. 如商品破损、少件、错发或质量问题，请提供照片或视频、外包装和快递面单照片。"""


def quick_answer(message, history=None, user_id=None):
    text = message.strip().lower()
    if not text:
        return after_sales_checklist()

    if is_acknowledgement(text):
        return "好的，有其他订单或售后问题可以继续发给小小易。"

    for keyword, answer in SMALL_TALK_ANSWERS.items():
        if keyword in text:
            return answer

    order_id = extract_order_id(text)
    if not order_id and is_standalone_service_intent(text):
        return standalone_service_answer(text, user_id=user_id)
    if not order_id and should_use_history_order(text):
        order_id = extract_order_id(text, history)
    if order_id:
        return order_contextual_answer(order_id, text, user_id=user_id)

    if text in ["你好", "您好", "hi", "hello", "在吗"]:
        return f"你好，我是{SHOP_NAME}售后客服 小小易。你可以问我订单查询、物流、退款、退货退款、换货、补发、破损少件或发票问题。"
    if contains_any(text, ["你是真人吗", "是真人吗", "真人吗", "你是真人", "你是人工吗"]):
        return REAL_PERSON_ANSWER
    if contains_any(text, ["你是谁", "你叫什么", "叫什么名字", "你是机器人", "你是真人吗", "介绍一下自己", "自我介绍"]):
        return IDENTITY_ANSWER
    if contains_any(text, ["能聊天吗", "可以聊天吗", "陪我聊", "闲聊"]):
        return "可以做简单交流。我是小小易，主要职责还是帮你处理星选商城售后问题；如果你有订单号或售后情况，可以直接发给我。"
    if contains_any(text, ["能做什么", "有什么功能", "可以问什么", "帮助", "help"]):
        return CAPABILITY_ANSWER
    if contains_any(text, ["正式售后", "售后标准", "标准流程", "客服标准"]):
        return FORMAL_SERVICE_FLOW
    if contains_any(text, ["售后客服"]) and contains_any(text, ["做什么", "主要工作", "平时", "职责", "流程"]):
        return AFTER_SALES_WORK_ANSWER
    if is_high_risk_question(text):
        return HIGH_RISK_ANSWER
    if contains_any(text, ["需要提供什么", "准备什么", "资料", "凭证", "怎么申请售后"]):
        return after_sales_checklist()

    if is_policy_or_process_question(text):
        if contains_any(text, ["换货"]):
            return EXCHANGE_PROCESS
        if contains_any(text, ["退货退款", "退货"]):
            return RETURN_REFUND_PROCESS
        if contains_any(text, ["退款", "多久到账", "退钱"]):
            return REFUND_PROCESS
        if contains_any(text, ["取消订单", "取消"]):
            return CANCEL_PROCESS
        if contains_any(text, ["补发", "少件", "漏发"]):
            return MISSING_PROCESS
        if contains_any(text, ["发票", "开票"]):
            return INVOICE_PROCESS
        if contains_any(text, ["催发货", "发货"]):
            return URGE_SHIPPING_PROCESS
        if contains_any(text, ["改地址", "修改地址", "地址"]):
            return ADDRESS_CHANGE_PROCESS
        if contains_any(text, ["拒收"]):
            return REJECT_PACKAGE_PROCESS
        if contains_any(text, ["价保", "保价", "降价"]):
            return PRICE_PROTECTION_PROCESS
        if contains_any(text, ["投诉", "工单"]):
            return COMPLAINT_PROCESS

    if contains_any(text, ["取消订单", "取消", "未发货", "拦截"]):
        return CANCEL_PROCESS
    if contains_any(text, ["催发货", "催发", "怎么还不发货", "什么时候发货"]):
        return URGE_SHIPPING_PROCESS
    if contains_any(text, ["改地址", "修改地址", "地址填错", "换地址"]):
        return ADDRESS_CHANGE_PROCESS
    if contains_any(text, ["拒收", "不收了", "快递到了不要"]):
        return REJECT_PACKAGE_PROCESS
    if contains_any(text, ["价保", "保价", "降价", "差价"]):
        return PRICE_PROTECTION_PROCESS
    if contains_any(text, ["退货退款", "退货", "退回", "寄回"]):
        return RETURN_REFUND_PROCESS
    if contains_any(text, ["仅退款", "退款", "多久到账", "退钱"]):
        return REFUND_PROCESS
    if contains_any(text, ["换货", "换尺码", "换颜色", "换一个"]):
        return EXCHANGE_PROCESS
    if contains_any(text, ["破损", "坏了", "质量问题", "漏液", "错发", "发错", "有瑕疵", "不能用"]):
        return DAMAGE_PROCESS
    if contains_any(text, ["少件", "漏发", "少发", "没收到全部", "缺少"]):
        return MISSING_PROCESS
    if contains_any(text, ["物流", "快递", "没更新", "丢件", "没收到", "到哪"]):
        if order_id:
            return order_answer(order_id, user_id=user_id)
        return LOGISTICS_PROCESS
    if contains_any(text, ["发票", "开票", "税号", "抬头"]):
        return INVOICE_PROCESS
    if contains_any(text, ["投诉", "不满意", "没人处理", "太慢", "升级处理"]):
        return COMPLAINT_PROCESS
    if contains_any(text, ["人工", "真人", "转人工", "工单"]):
        return human_handoff_answer(text, user_id=user_id)
    if contains_any(text, ["保修", "质保", "维修"]):
        return "部分电子类商品支持 1 年质保，具体以商品页面说明为准。请提供订单号、商品名称和故障说明，我可以帮你判断处理方式。"
    if contains_any(text, ["七天", "7天", "无理由", "不想要"]):
        return "已签收商品通常可在 7 天内申请无理由退货，但商品需不影响二次销售。定制商品、生鲜食品、虚拟商品、已拆封的一次性卫生用品等不支持无理由退货。"
    return None


def is_domain_question(message):
    text = message.lower()
    keywords = [
        "订单", "物流", "快递", "退款", "退货", "换货", "补发", "售后", "发票",
        "破损", "质量", "漏发", "少件", "取消", "签收", "人工", "投诉",
        "保修", "质保", "订单号", "ec2026", "催发货", "发货", "改地址",
        "修改地址", "拒收", "价保", "保价", "差价", "工单", "return", "refund", "exchange",
        "invoice", "shipping", "tracking", "after-sales",
    ]
    return contains_any(text, keywords)


def is_high_risk_question(message):
    text = message.lower()
    keywords = [
        "诊断", "吃什么药", "处方", "病", "法律", "起诉", "合同", "赔偿",
        "投资", "股票", "基金", "贷款", "保险", "税务", "medical", "legal",
        "investment", "stock",
    ]
    return contains_any(text, keywords)


def clean_answer(content):
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if "答：" in content:
        content = content.split("答：")[-1].strip()
    if "最终答案：" in content:
        content = content.split("最终答案：")[-1].strip()
    reasoning_markers = [
        "首先，", "回顾", "我需要", "根据要求", "用户的问题是", "角色设定",
        "回答要求", "提示词", "这是一个", "根据我的角色",
    ]
    if any(marker in content[:80] for marker in reasoning_markers):
        sentences = re.split(r"(?<=[。！？])", content)
        useful = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
            and not any(marker in sentence for marker in reasoning_markers)
            and "知识库" not in sentence
            and "推理" not in sentence
        ]
        content = "".join(useful[:4]).strip() or "请提供订单号和具体售后问题，我可以帮你查询或判断处理方案。"
    forbidden_markers = [
        "根据要求", "角色设定", "回答要求", "提示词", "用户要求",
        "回答尽量", "不要复述规则", "不要假装", "只输出给用户",
        "如果用户的问题和售后无关", "这看起来像是一个测试", "根据规则",
        "我的角色是", "规则要求",
    ]
    if any(marker in content for marker in forbidden_markers):
        content = "我可以简单聊几句，但主要还是帮你处理星选商城的订单、物流、退款、退货、换货等售后问题。你也可以直接把订单号或售后问题发给我。"
    return content


def log_answer(message, answer, mode, user_id=None, channel="web", session_id=None, evidence_files=None):
    chat_history.append({"user": message, "assistant": answer})
    logger.info(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "role": "assistant",
        "content": answer,
        "mode": mode,
    }, ensure_ascii=False))
    try:
        record_qa(message, answer, mode)
    except Exception as exc:
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "event": "learning_record_failed",
            "error": str(exc),
        }, ensure_ascii=False))
    try:
        session_id = session_id or user_id or "web_guest"
        save_message(session_id, "user", message, user_id=user_id, channel=channel)
        save_message(session_id, "assistant", answer, user_id=user_id, channel=channel)
        order_id = extract_order_id(message)
        ticket_id = None
        if should_create_ticket(message) and "工单号" not in answer:
            ticket_id = create_ticket(
                message,
                user_id=user_id,
                order_id=order_id,
                priority="高" if contains_any(message, ["投诉", "不满意", "太慢"]) else "普通",
            )
        for file_path in evidence_files or []:
            save_evidence_file(
                file_path,
                user_id=user_id,
                order_id=order_id,
                ticket_id=ticket_id,
                purpose="售后凭证",
            )
    except Exception as exc:
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "event": "app_database_record_failed",
            "error": str(exc),
        }, ensure_ascii=False))


def model_chat(message, history=None):
    recent_messages = []
    if history:
        for item in history[-6:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                recent_messages.append({"role": role, "content": content})

    prompt = message
    if is_high_risk_question(message):
        prompt = (
            f"{message}\n\n"
            "请只给通用性提醒，不要给专业诊断、法律结论或投资建议。"
        )

    content = chat_completion(
        messages=[
            {"role": "system", "content": GENERAL_CHAT_MESSAGE},
            *recent_messages,
            {"role": "user", "content": f"/no_think\n{prompt}"},
        ],
        temperature=0.3,
        max_tokens=160,
    )
    return clean_answer(content)


def chat(message, history, user_id=None, channel="web", session_id=None, evidence_files=None):
    fast_answer = quick_answer(message, history, user_id=user_id)
    if fast_answer:
        log_answer(message, fast_answer, "quick_answer", user_id=user_id, channel=channel, session_id=session_id, evidence_files=evidence_files)
        return fast_answer

    learned_answer = find_learned_answer(message)
    if learned_answer:
        log_answer(message, learned_answer, "learned_answer", user_id=user_id, channel=channel, session_id=session_id, evidence_files=evidence_files)
        return learned_answer

    if not is_domain_question(message):
        answer = model_chat(message, history)
        log_answer(message, answer, "general_model_chat", user_id=user_id, channel=channel, session_id=session_id, evidence_files=evidence_files)
        return answer

    related_docs = retriever.invoke(message)
    context = "\n\n".join(doc.page_content for doc in related_docs)
    prompt = f"""/no_think
请根据下面的售后知识库资料，用中文快速回答用户问题。
要求：
1. 只输出最终答案，不要解释推理过程。
2. 回答控制在 3 到 5 句话。
3. 如果缺少订单号、凭证或必要信息，请明确提醒用户补充。
4. 如果资料里没有答案，就说“目前售后知识库中没有相关信息”。

售后知识库资料：
{context}

用户问题：
{message}
"""
    content = chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=180,
    )
    answer = clean_answer(content)
    log_answer(message, answer, "rag_answer", user_id=user_id, channel=channel, session_id=session_id, evidence_files=evidence_files)
    return answer


def rows_for_orders(user_id=None):
    return [
        [
            item.get("order_id", ""),
            item.get("product", ""),
            item.get("status", ""),
            item.get("logistics_no", ""),
            item.get("detail", ""),
        ]
        for item in list_orders(user_id)
    ]


def rows_for_tickets():
    return [
        [
            item.get("ticket_id", ""),
            item.get("user_id", ""),
            item.get("order_id", ""),
            item.get("category", ""),
            item.get("status", ""),
            item.get("priority", ""),
            item.get("latest_progress", ""),
            item.get("updated_at", ""),
        ]
        for item in list_tickets()
    ]


def rows_for_conversations():
    return [
        [
            item.get("created_at", ""),
            item.get("channel", ""),
            item.get("user_id", ""),
            item.get("session_id", ""),
            item.get("role", ""),
            item.get("content", ""),
        ]
        for item in list_conversations()
    ]


def rows_for_evidence():
    return [
        [
            item.get("created_at", ""),
            item.get("user_id", ""),
            item.get("order_id", ""),
            item.get("ticket_id", ""),
            item.get("original_name", ""),
            item.get("saved_path", ""),
        ]
        for item in list_evidence_files()
    ]


def history_choices(limit=12):
    items = []
    seen = set()
    for item in list_conversations(limit=80):
        if item.get("role") != "user":
            continue
        content = (item.get("content") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)
        items.append(content)
        if len(items) >= limit:
            break
    return items or ["暂无历史对话"]


def load_history_chat(selected):
    if not selected or selected == "暂无历史对话":
        return gr.update(value=[], visible=False), gr.update(visible=True), ""

    rows = list(reversed(list_conversations(limit=300)))
    match_index = None
    for index, item in enumerate(rows):
        if item.get("role") == "user" and (item.get("content") or "").strip() == selected:
            match_index = index

    if match_index is None:
        return gr.update(value=[], visible=False), gr.update(visible=True), ""

    snippet = []
    for item in rows[match_index:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "user" and snippet:
            break
        if role in {"user", "assistant"}:
            snippet.append({"role": role, "content": content})
        if len(snippet) >= 2 and role == "assistant":
            break

    return gr.update(value=snippet, visible=True), gr.update(visible=False), ""


def service_overview_html(user_id=None):
    return ""


def login_user(phone, password):
    user = get_user_by_phone((phone or "").strip(), (password or "").strip())
    if not user:
        return None, "登录失败，请使用示例手机号 13800000001 / 密码 123456。", [], []

    status = f"已登录：{user['name']}（{user['phone']}）"
    return user, status, rows_for_orders(user["user_id"]), [
        {"role": "assistant", "content": f"你好，{user['name']}。我是小小易，可以帮你处理订单、物流、退款、退货、换货和投诉等售后问题。"}
    ]


def normalize_uploaded_files(files):
    if not files:
        return []
    if not isinstance(files, list):
        files = [files]

    paths = []
    for item in files:
        if isinstance(item, str):
            paths.append(item)
        elif hasattr(item, "name"):
            paths.append(item.name)
        elif isinstance(item, dict) and item.get("path"):
            paths.append(item["path"])
    return paths


def should_show_evidence_upload(message):
    text = (message or "").strip().lower()
    if not text:
        return False
    return contains_any(text, [
        "破损", "坏了", "质量问题", "漏液", "错发", "发错", "发错货",
        "少件", "漏发", "少发", "缺少", "没收到全部", "凭证", "照片",
        "图片", "视频", "面单", "包装", "瑕疵", "不能用",
    ])


def evidence_upload_update(message):
    return gr.update(visible=should_show_evidence_upload(message))


def show_evidence_upload():
    return gr.update(visible=True)


def send_message_ui(message, history, user, files):
    text = (message or "").strip()
    if not text and not files:
        user_id = user.get("user_id") if user else None
        return (
            gr.update(value=history or [], visible=bool(history)),
            "",
            None,
            rows_for_orders(user_id),
            service_overview_html(user_id),
            gr.update(visible=not bool(history)),
            gr.update(choices=history_choices(), value=None),
        )

    user_id = user.get("user_id") if user else None
    uploaded_paths = normalize_uploaded_files(files)
    evidence_note = ""
    if uploaded_paths:
        names = "、".join(Path(path).name for path in uploaded_paths)
        evidence_note = f"\n用户已上传售后凭证：{names}"

    ask_text = text or "我上传了售后凭证，请帮我登记处理。"
    answer = chat(
        ask_text + evidence_note,
        history or [],
        user_id=user_id,
        channel="web",
        session_id=user_id or "web_guest",
        evidence_files=uploaded_paths,
    )
    updated = (history or []) + [
        {"role": "user", "content": ask_text},
        {"role": "assistant", "content": answer},
    ]
    return (
        gr.update(value=updated, visible=True),
        "",
        gr.update(value=None, visible=False),
        rows_for_orders(user_id),
        service_overview_html(user_id),
        gr.update(visible=False),
        gr.update(choices=history_choices(), value=None),
    )


def reset_chat_ui(user):
    user_id = user.get("user_id") if user else None
    return (
        gr.update(value=[], visible=False),
        "",
        gr.update(value=None, visible=False),
        rows_for_orders(user_id),
        service_overview_html(user_id),
        gr.update(visible=True),
        gr.update(choices=history_choices(), value=None),
    )


def refresh_backend():
    return rows_for_tickets(), rows_for_conversations(), rows_for_evidence()


def build_demo():
    demo_user = default_demo_user()
    demo_user_id = demo_user.get("user_id") if demo_user else None
    demo_user_name = demo_user.get("name", "用户") if demo_user else "用户"
    greeting = []
    with gr.Blocks(title="小小易，星选商城售后客服", analytics_enabled=False, css=APP_CSS) as app:
        user_state = gr.State(demo_user)
        gr.Markdown("# 小小易，星选商城售后客服", elem_id="app_title")

        with gr.Tabs():
            with gr.Tab("用户客服"):
                with gr.Row(elem_classes="customer-layout"):
                    with gr.Column(scale=1, min_width=240, elem_classes="history-sidebar"):
                        new_chat_btn = gr.Button("新对话", elem_classes="new-chat-btn")
                        history_panel = gr.Radio(
                            label="历史对话",
                            choices=history_choices(),
                            value=None,
                            elem_classes="history-radio",
                        )
                    with gr.Column(scale=4):
                        with gr.Column(elem_classes="simple-shell"):
                            gr.Markdown(
                                f"### 小小易\n{demo_user_name}，已接入星选商城售后系统",
                                elem_classes="simple-header",
                            )
                            overview = gr.HTML(service_overview_html(demo_user_id))
                            orders_table = gr.State(rows_for_orders(demo_user_id))
                            with gr.Column(elem_classes="home-stage"):
                                with gr.Column(elem_classes="prompt-panel") as prompt_panel:
                                    gr.HTML("<h2>我是小小易，有什么我能帮到你的吗？</h2>")
                                    with gr.Row(elem_classes="quick-action-row"):
                                        quick_logistics = gr.Button("订单 EC20260702002 物流到哪了？")
                                        quick_refund = gr.Button("我要申请退款")
                                        quick_exchange = gr.Button("我要换货")
                                        quick_evidence = gr.Button("商品破损了怎么办？")
                                        quick_handoff = gr.Button("我要转人工")
                                    with gr.Row(elem_classes="quick-action-row"):
                                        quick_cancel = gr.Button("订单还没发货，可以取消吗？")
                                        quick_address = gr.Button("已发货订单怎么改地址？")
                                        quick_invoice = gr.Button("我要开发票")
                                with gr.Column(elem_classes="input-dock"):
                                    chatbot = gr.Chatbot(
                                        type="messages",
                                        height=560,
                                        label="客服对话",
                                        value=greeting,
                                        show_label=False,
                                        container=False,
                                        layout="bubble",
                                        bubble_full_width=False,
                                        elem_id="simple_chatbot",
                                        visible=False,
                                    )
                                    files = gr.File(
                                        label="上传售后凭证（照片、视频、快递面单等）",
                                        file_count="multiple",
                                        visible=False,
                                        elem_classes="simple-upload",
                                    )
                                    with gr.Row(elem_classes="simple-input-bar"):
                                        message = gr.Textbox(
                                            placeholder="请输入订单号或售后问题...",
                                            label="",
                                            show_label=False,
                                            scale=12,
                                            max_lines=3,
                                            elem_classes="simple-input",
                                        )
                                        upload_btn = gr.Button("+", scale=1, min_width=44, elem_classes="simple-plus-btn")
                                        send_btn = gr.Button("发送", scale=2, min_width=72, elem_classes="simple-send-btn")

                                    with gr.Accordion("常用问题", open=False, elem_classes="quick-questions"):
                                        gr.Examples(
                                            examples=[
                                                "订单 EC20260702002 物流到哪了？",
                                                "订单 EC20260702003 怎么还不发货？",
                                                "订单 EC20260702002 我想改地址",
                                                "商品破损了怎么办？",
                                                "我要投诉，处理太慢了",
                                            ],
                                            inputs=message,
                                        )

            with gr.Tab("后台管理"):
                with gr.Column(elem_classes="backend-panel"):
                    with gr.Row(elem_classes="backend-toolbar"):
                        gr.Markdown("### 工单、会话和凭证")
                        refresh_btn = gr.Button("刷新后台数据", scale=0, min_width=120)
                    tickets_table = gr.Dataframe(
                        headers=["工单号", "用户", "订单号", "类型", "状态", "优先级", "进度", "更新时间"],
                        value=rows_for_tickets(),
                        label="工单列表",
                    )
                    conversations_table = gr.Dataframe(
                        headers=["时间", "渠道", "用户", "会话", "角色", "内容"],
                        value=rows_for_conversations(),
                        label="会话记录",
                    )
                    evidence_table = gr.Dataframe(
                        headers=["时间", "用户", "订单号", "工单号", "原文件名", "保存路径"],
                        value=rows_for_evidence(),
                        label="售后凭证",
                    )

        send_btn.click(
            send_message_ui,
            inputs=[message, chatbot, user_state, files],
            outputs=[chatbot, message, files, orders_table, overview, prompt_panel, history_panel],
            api_name=False,
        )
        message.submit(
            send_message_ui,
            inputs=[message, chatbot, user_state, files],
            outputs=[chatbot, message, files, orders_table, overview, prompt_panel, history_panel],
            api_name=False,
        )
        new_chat_btn.click(
            reset_chat_ui,
            inputs=[user_state],
            outputs=[chatbot, message, files, orders_table, overview, prompt_panel, history_panel],
            api_name=False,
        )
        history_panel.change(
            load_history_chat,
            inputs=[history_panel],
            outputs=[chatbot, prompt_panel, message],
            api_name=False,
        )
        message.change(
            evidence_upload_update,
            inputs=[message],
            outputs=[files],
            api_name=False,
        )
        upload_btn.click(
            show_evidence_upload,
            inputs=[],
            outputs=[files],
            api_name=False,
        )
        quick_logistics.click(
            lambda: "订单 EC20260702002 物流到哪了？",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_refund.click(
            lambda: "我要申请退款",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_exchange.click(
            lambda: "我要换货",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_evidence.click(
            lambda: "商品破损了怎么办？",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_handoff.click(
            lambda: "我要转人工",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_cancel.click(
            lambda: "订单 EC20260702003 可以取消吗？",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_address.click(
            lambda: "订单 EC20260702002 我想改地址",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        quick_invoice.click(
            lambda: "我要开发票",
            inputs=[],
            outputs=[message],
            api_name=False,
        )
        refresh_btn.click(
            refresh_backend,
            inputs=[],
            outputs=[tickets_table, conversations_table, evidence_table],
            api_name=False,
        )

    return app


demo = build_demo()


if __name__ == "__main__":
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)
