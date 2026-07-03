import time

from main import chat


TEST_CASES = [
    ("问候", "你好", []),
    ("身份介绍", "你是谁？", []),
    ("名字", "你叫什么名字？", []),
    ("简单闲聊", "你能聊天吗？", []),
    ("感谢", "谢谢你", []),
    ("告别", "再见", []),
    ("能力说明", "你能做什么？", []),
    ("正式流程", "正式售后客服标准流程是什么？", []),
    ("订单查询", "订单 EC20260702002 物流到哪了？", []),
    ("只发订单号", "EC20260702001", []),
    ("模糊订单查询", "帮我查一下EC20260702003", []),
    ("取消订单", "未发货订单可以取消吗？", []),
    ("订单取消", "订单 EC20260702003 能取消吗？", []),
    ("催发货", "订单 EC20260702003 怎么还不发货？", []),
    ("修改地址", "订单 EC20260702002 我想改地址", []),
    ("拒收", "快递到了我不想要，可以拒收吗？", []),
    ("价保", "我想申请价保", []),
    ("退货退款", "我想退货退款，需要怎么操作？", []),
    ("仅退款", "退款多久到账？", []),
    ("换货", "我要换货怎么处理？", []),
    ("破损", "商品破损了怎么办？", []),
    ("少件漏发", "少发了一件商品怎么办？", []),
    ("物流异常", "快递 72 小时没更新怎么办？", []),
    ("发票", "我需要补开发票", []),
    ("质保", "电子产品保修多久？", []),
    (
        "追问订单",
        "它现在什么状态？",
        [
            {"role": "user", "content": "帮我查订单 EC20260702004"},
            {"role": "assistant", "content": "订单 EC20260702004 正在退货退款处理中。"},
        ],
    ),
    (
        "确认语不重复订单",
        "好的",
        [
            {"role": "user", "content": "订单 EC20260702002 物流到哪了？"},
            {"role": "assistant", "content": "订单 EC20260702002 的商品是夏季纯棉 T 恤，当前状态：已发货。"},
        ],
    ),
    (
        "流程问题不继承订单",
        "换货流程",
        [
            {"role": "user", "content": "订单 EC20260702002 物流到哪了？"},
            {"role": "assistant", "content": "订单 EC20260702002 的商品是夏季纯棉 T 恤，当前状态：已发货。"},
        ],
    ),
    (
        "退款泛化问题不继承订单",
        "退款",
        [
            {"role": "user", "content": "订单 EC20260702002 物流到哪了？"},
            {"role": "assistant", "content": "订单 EC20260702002 的商品是夏季纯棉 T 恤，当前状态：已发货。"},
        ],
    ),
    ("转人工", "我要转人工", []),
    ("投诉升级", "我要投诉，处理太慢了", []),
    ("普通聊天", "讲个简短的笑话", []),
    ("常识聊天", "电商售后客服平时主要做什么？", []),
    ("高风险提醒", "我能买哪只股票赚钱？", []),
]

CASE_FORBIDDEN_MARKERS = {
    "确认语不重复订单": ["EC20260702002", "物流单号"],
    "流程问题不继承订单": ["EC20260702002", "物流单号", "夏季纯棉 T 恤"],
    "退款泛化问题不继承订单": ["EC20260702002", "物流单号", "夏季纯棉 T 恤"],
}

FORBIDDEN_MARKERS = [
    "<think>",
    "根据要求",
    "角色设定",
    "回答要求",
    "提示词",
    "用户的问题是",
    "只输出给用户",
    "不要复述规则",
]


if __name__ == "__main__":
    failed = 0
    for name, question, history in TEST_CASES:
        start = time.perf_counter()
        answer = chat(question, history)
        elapsed = time.perf_counter() - start
        case_forbidden = CASE_FORBIDDEN_MARKERS.get(name, [])
        ok = (
            bool(answer)
            and not any(marker in answer for marker in FORBIDDEN_MARKERS)
            and not any(marker in answer for marker in case_forbidden)
        )
        failed += 0 if ok else 1
        status = "PASS" if ok else "FAIL"
        preview = answer.replace("\n", " ")[:100] if answer else ""
        print(f"{status}\t{name}\t{elapsed:.4f}s\t{preview}")

    if failed:
        raise SystemExit(f"{failed} test case(s) failed.")
