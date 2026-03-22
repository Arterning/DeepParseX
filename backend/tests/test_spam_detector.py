#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
垃圾邮件检测器测试脚本
"""


import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.utils.spam_detector import spam_detector


def print_result(title: str, result: int, score: float, reason: str):
    """打印检测结果"""
    result_text = {
        0: "✅ 正常邮件",
        1: "🚫 垃圾邮件",
        2: "⚠️  疑似垃圾邮件"
    }
    print(f"\n{'='*70}")
    print(f"测试场景: {title}")
    print(f"检测结果: {result_text.get(result, '未知')}")
    print(f"置信度分数: {score:.1f}/100")
    print(f"检测原因: {reason}")
    print(f"{'='*70}")


def test_normal_emails():
    """测试正常邮件"""
    print("\n\n🔵 测试正常邮件场景")
    print("=" * 70)

    # 测试1: 普通工作邮件
    result, score, reason = spam_detector.detect(
        subject="关于项目进度的更新",
        body="您好，这是本周项目进度的更新报告。项目进展顺利，预计下周可以完成第一阶段的开发工作。",
        sender="zhang.san@company.com"
    )
    print_result("普通工作邮件", result, score, reason)

    # 测试2: 朋友邮件
    result, score, reason = spam_detector.detect(
        subject="周末聚会",
        body="嗨，周末有空吗？我们几个老同学想聚一聚，地点在老地方，时间是周六晚上7点。",
        sender="friend@gmail.com"
    )
    print_result("朋友邮件", result, score, reason)

    # 测试3: 系统通知邮件
    result, score, reason = spam_detector.detect(
        subject="您的订单已发货",
        body="尊敬的客户，您的订单已经发货，快递单号为：1234567890，预计3-5天送达。",
        sender="service@jd.com"
    )
    print_result("系统通知邮件", result, score, reason)


def test_spam_emails():
    """测试垃圾邮件"""
    print("\n\n🔴 测试垃圾邮件场景")
    print("=" * 70)

    # 测试1: 中奖诈骗邮件
    result, score, reason = spam_detector.detect(
        subject="恭喜您中奖了！！！点击领取大奖！！！",
        body="恭喜您获得了100万元大奖！请立即点击链接领取奖金，限时24小时！加微信：xxx 立即领取！",
        sender="admin@free-domain.tk"
    )
    print_result("中奖诈骗邮件", result, score, reason)

    # 测试2: 色情垃圾邮件
    result, score, reason = spam_detector.detect(
        subject="成人内容，18岁以下禁止观看",
        body="色情内容，点击查看更多成人视频...",
        sender="noreply@spam-site.ml"
    )
    print_result("色情垃圾邮件", result, score, reason)

    # 测试3: 赌博邮件
    result, score, reason = spam_detector.detect(
        subject="每天赚钱1000元，博彩网站",
        body="免费注册赌博网站，日赚千元不是梦！六合彩、彩票开奖，点击进入！",
        sender="abc123xyz456@randomdomain.ga"
    )
    print_result("赌博邮件", result, score, reason)

    # 测试4: 假发票邮件
    result, score, reason = spam_detector.detect(
        subject="代开发票，刻章办证",
        body="专业代开各种发票，增值税发票、普通发票应有尽有。可办理各种证件，身份证、银行卡、驾驶证等。",
        sender="service@fake-invoice.com"
    )
    print_result("假发票邮件", result, score, reason)

    # 测试5: 贷款垃圾邮件
    result, score, reason = spam_detector.detect(
        subject="无抵押贷款，当天放款",
        body="无需抵押，快速贷款，当天放款，利息低，额度高。点击立即申请！",
        sender="loan@easy-money.com"
    )
    print_result("贷款垃圾邮件", result, score, reason)


def test_suspicious_emails():
    """测试可疑邮件"""
    print("\n\n🟡 测试疑似垃圾邮件场景")
    print("=" * 70)

    # 测试1: 包含一些营销词汇的邮件
    result, score, reason = spam_detector.detect(
        subject="限时优惠活动",
        body="尊敬的用户，我们正在进行限时优惠活动，欢迎选购。活动时间有限，请抓紧时间。",
        sender="marketing@legitimate-company.com"
    )
    print_result("营销邮件", result, score, reason)

    # 测试2: 包含多个链接的邮件
    result, score, reason = spam_detector.detect(
        subject="最新资讯",
        body="查看更多：http://link1.com http://link2.com http://link3.com http://link4.com http://link5.com",
        sender="news@newsletter.com"
    )
    print_result("包含多个链接的邮件", result, score, reason)

    # 测试3: 全大写的邮件
    result, score, reason = spam_detector.detect(
        subject="URGENT MESSAGE FOR YOU",
        body="PLEASE CHECK THIS IMPORTANT MESSAGE IMMEDIATELY",
        sender="admin@company.com"
    )
    print_result("全大写邮件", result, score, reason)


def test_edge_cases():
    """测试边界情况"""
    print("\n\n⚪ 测试边界情况")
    print("=" * 70)

    # 测试1: 空邮件
    result, score, reason = spam_detector.detect(
        subject="",
        body="",
        sender="test@test.com"
    )
    print_result("空邮件", result, score, reason)

    # 测试2: 只有主题的邮件
    result, score, reason = spam_detector.detect(
        subject="测试主题",
        body="",
        sender="test@test.com"
    )
    print_result("只有主题的邮件", result, score, reason)

    # 测试3: 只有正文的邮件
    result, score, reason = spam_detector.detect(
        subject="",
        body="这是一封正常的邮件内容",
        sender="test@test.com"
    )
    print_result("只有正文的邮件", result, score, reason)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("垃圾邮件检测器测试")
    print("="*70)

    # 运行所有测试
    test_normal_emails()
    test_spam_emails()
    test_suspicious_emails()
    test_edge_cases()

    print("\n\n" + "="*70)
    print("测试完成！")
    print("="*70)
