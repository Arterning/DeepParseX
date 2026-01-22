#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
垃圾邮件检测器
基于规则和关键词检测邮件是否为垃圾邮件
"""

import re
from typing import Tuple


class SpamDetector:
    """垃圾邮件检测器"""

    # 垃圾邮件常见关键词（中文）
    SPAM_KEYWORDS_ZH = [
        '中奖', '免费', '赚钱', '兼职', '代开发票', '贷款', '办证',
        '加QQ', '加微信', '点击领取', '限时优惠', '火爆热卖',
        '成人', '色情', '赌博', '博彩', '六合彩', '彩票',
        '发财', '致富', '暴利', '高薪', '日赚', '月入',
        '包过', '包治', '特效药', '增高', '减肥', '丰胸',
        '发票', '刻章', '办理', '证件', '身份证', '银行卡',
        '游戏币', '代练', '外挂', '私服', '枪支', '毒品',
        '走私', '黑市', '假货', '高仿', 'A货', '复刻',
        'urgent', 'winner', 'congratulations', 'prize', 'lottery'
    ]

    # 垃圾邮件常见关键词（英文）
    SPAM_KEYWORDS_EN = [
        'viagra', 'cialis', 'pharmacy', 'pills', 'drugs',
        'casino', 'gambling', 'poker', 'lottery', 'winner',
        'congratulations', 'prize', 'reward', 'claim now',
        'click here', 'act now', 'limited time', 'urgent',
        'make money', 'work from home', 'earn cash', 'get paid',
        'free money', 'no cost', 'risk free', '100% free',
        'weight loss', 'lose weight', 'diet pills',
        'enlarge', 'enhancement', 'adult content',
        'refinance', 'mortgage', 'credit card', 'loan',
        'invoice', 'billing', 'payment failed', 'account suspended'
    ]

    # 可疑发件人域名特征
    SUSPICIOUS_DOMAIN_PATTERNS = [
        r'\.tk$',  # 免费域名
        r'\.ml$',
        r'\.ga$',
        r'\.cf$',
        r'\.gq$',
        r'\d{5,}',  # 包含大量数字的域名
        r'[a-z0-9]{20,}',  # 随机字符串域名
    ]

    # 可疑发件人名称特征
    SUSPICIOUS_SENDER_PATTERNS = [
        r'admin@',
        r'noreply@',
        r'no-reply@',
        r'support@.*\.(tk|ml|ga|cf|gq)',  # 免费域名的支持邮箱
        r'[a-z0-9]{15,}@',  # 随机字符串邮箱
    ]

    # 高危垃圾邮件关键词（权重更高）
    HIGH_RISK_KEYWORDS = [
        '色情', '赌博', '博彩', '枪支', '毒品', '走私',
        '代开发票', '刻章', '假证', '银行卡', '身份证',
        'viagra', 'casino', 'gambling', 'drugs', 'adult content'
    ]

    @staticmethod
    def detect(subject: str = '', body: str = '', sender: str = '') -> Tuple[int, float, str]:
        """
        检测邮件是否为垃圾邮件

        Args:
            subject: 邮件主题
            body: 邮件正文
            sender: 发件人邮箱

        Returns:
            Tuple[int, float, str]: (检测结果, 置信度分数, 检测原因)
            - 检测结果: 0=正常邮件, 1=垃圾邮件, 2=疑似垃圾邮件
            - 置信度分数: 0-100，分数越高越可能是垃圾邮件
            - 检测原因: 说明为什么判定为垃圾邮件
        """
        score = 0.0
        reasons = []

        # 统一转换为小写进行检测
        subject_lower = subject.lower() if subject else ''
        body_lower = body.lower() if body else ''
        sender_lower = sender.lower() if sender else ''

        # 1. 检测主题中的垃圾邮件关键词
        subject_spam_count = 0
        subject_high_risk_count = 0

        for keyword in SpamDetector.SPAM_KEYWORDS_ZH + SpamDetector.SPAM_KEYWORDS_EN:
            if keyword.lower() in subject_lower:
                subject_spam_count += 1
                if keyword in SpamDetector.HIGH_RISK_KEYWORDS:
                    subject_high_risk_count += 1
                    score += 15  # 主题中的高危关键词权重更高
                else:
                    score += 10  # 主题中的关键词权重较高

        if subject_spam_count > 0:
            reasons.append(f"主题包含{subject_spam_count}个垃圾邮件关键词")

        # 2. 检测正文中的垃圾邮件关键词
        body_spam_count = 0
        body_high_risk_count = 0

        # 只检测正文前1000字符，避免性能问题
        body_sample = body_lower[:1000] if body_lower else ''

        for keyword in SpamDetector.SPAM_KEYWORDS_ZH + SpamDetector.SPAM_KEYWORDS_EN:
            if keyword.lower() in body_sample:
                body_spam_count += 1
                if keyword in SpamDetector.HIGH_RISK_KEYWORDS:
                    body_high_risk_count += 1
                    score += 8  # 正文中的高危关键词
                else:
                    score += 5  # 正文中的关键词权重较低

        if body_spam_count > 0:
            reasons.append(f"正文包含{body_spam_count}个垃圾邮件关键词")

        # 3. 检测发件人信息
        sender_suspicious = False

        # 检测可疑域名
        for pattern in SpamDetector.SUSPICIOUS_DOMAIN_PATTERNS:
            if re.search(pattern, sender_lower):
                score += 12
                sender_suspicious = True
                reasons.append("发件人域名可疑")
                break

        # 检测可疑发件人
        for pattern in SpamDetector.SUSPICIOUS_SENDER_PATTERNS:
            if re.search(pattern, sender_lower):
                score += 8
                sender_suspicious = True
                reasons.append("发件人邮箱格式可疑")
                break

        # 4. 检测主题特征
        # 全大写主题（英文）
        if subject and len(subject) > 5:
            upper_count = sum(1 for c in subject if c.isupper())
            if upper_count / len(subject) > 0.7:
                score += 10
                reasons.append("主题包含大量大写字母")

        # 主题中包含大量感叹号或问号
        if subject:
            exclamation_count = subject.count('!') + subject.count('！')
            question_count = subject.count('?') + subject.count('？')
            if exclamation_count >= 3 or question_count >= 3:
                score += 8
                reasons.append("主题包含大量感叹号或问号")

        # 主题中包含大量特殊符号
        if subject:
            special_chars = re.findall(r'[★☆●○◆◇■□▲△▼▽◎※]', subject)
            if len(special_chars) >= 3:
                score += 8
                reasons.append("主题包含大量特殊符号")

        # 5. 检测正文特征
        if body:
            # 正文中包含大量URL链接
            url_count = len(re.findall(r'https?://[^\s]+', body_sample))
            if url_count >= 5:
                score += 10
                reasons.append(f"正文包含{url_count}个URL链接")
            elif url_count >= 3:
                score += 5

        # 6. 空主题或空正文（可疑）
        if not subject or len(subject.strip()) == 0:
            score += 5
            reasons.append("邮件主题为空")

        if not body or len(body.strip()) == 0:
            score += 5
            reasons.append("邮件正文为空")

        # 7. 综合判定
        # 如果包含高危关键词，直接判定为垃圾邮件
        if subject_high_risk_count > 0 or body_high_risk_count > 0:
            score = max(score, 80)  # 确保分数至少为80
            reasons.append("包含高危垃圾邮件关键词")

        # 根据分数判定结果
        if score >= 60:
            result = 1  # 垃圾邮件
        elif score >= 30:
            result = 2  # 疑似垃圾邮件
        else:
            result = 0  # 正常邮件

        # 限制分数在0-100之间
        score = min(100, max(0, score))

        # 生成检测原因说明
        reason_text = "; ".join(reasons) if reasons else "无明显垃圾邮件特征"

        return result, score, reason_text

    @staticmethod
    def add_custom_keywords(keywords: list):
        """
        添加自定义垃圾邮件关键词

        Args:
            keywords: 要添加的关键词列表
        """
        SpamDetector.SPAM_KEYWORDS_ZH.extend(keywords)

    @staticmethod
    def add_high_risk_keywords(keywords: list):
        """
        添加自定义高危垃圾邮件关键词

        Args:
            keywords: 要添加的高危关键词列表
        """
        SpamDetector.HIGH_RISK_KEYWORDS.extend(keywords)


# 创建全局检测器实例
spam_detector = SpamDetector()
