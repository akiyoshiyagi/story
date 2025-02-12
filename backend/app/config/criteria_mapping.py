"""
評価基準のマッピングを定義するモジュール
"""
from ..models.criteria_info import CriteriaInfo
from typing import List

# 評価カテゴリの優先順位定数
CRITERIA_PRIORITY = {
    "FULL_TEXT_RHETORIC": 1,
    "SUMMARY_LOGIC_FLOW": 2,
    "SUMMARY_INTERNAL_LOGIC": 3,
    "SUMMARY_STORY_LOGIC": 4,
    "STORY_INTERNAL_LOGIC": 5,
    "DETAIL_RHETORIC": 6
}

# 評価基準のマッピング
CRITERIA_MAPPING = {
    "FULL_TEXT_RHETORIC": CriteriaInfo(
        id="FULL_TEXT_RHETORIC",
        display_name="全文修辞表現",
        priority=CRITERIA_PRIORITY["FULL_TEXT_RHETORIC"],
        criteria_ids=["最低限の修辞表現", "修辞表現"],
        max_score=20.0  # 20点
    ),
    "SUMMARY_LOGIC_FLOW": CriteriaInfo(
        id="SUMMARY_LOGIC_FLOW",
        display_name="サマリーの論理展開",
        priority=CRITERIA_PRIORITY["SUMMARY_LOGIC_FLOW"],
        criteria_ids=["前回の振り返りの有無", "SCQA有無", "転換の接続詞の重複利用"],
        max_score=25.0  # 25点
    ),
    "SUMMARY_INTERNAL_LOGIC": CriteriaInfo(
        id="SUMMARY_INTERNAL_LOGIC",
        display_name="サマリー単体の論理",
        priority=CRITERIA_PRIORITY["SUMMARY_INTERNAL_LOGIC"],
        criteria_ids=["接続詞の妥当性", "サマリーレイヤーに不適な接続詞の有無", "直前のサマリーとの論理的連続性"],
        max_score=15.0  # 15点
    ),
    "SUMMARY_STORY_LOGIC": CriteriaInfo(
        id="SUMMARY_STORY_LOGIC",
        display_name="サマリーとストーリー間の論理",
        priority=CRITERIA_PRIORITY["SUMMARY_STORY_LOGIC"],
        criteria_ids=["メッセージレイヤーの逐次的展開性", "逐次的展開の評価", "根拠s, 詳細s⇔主張"],
        max_score=20.0  # 20点
    ),
    "STORY_INTERNAL_LOGIC": CriteriaInfo(
        id="STORY_INTERNAL_LOGIC",
        display_name="ストーリー単体の論理",
        priority=CRITERIA_PRIORITY["STORY_INTERNAL_LOGIC"],
        criteria_ids=["接続詞の適切性", "転換の接続詞の二重利用", "無駄なナンバリングの回避"],
        max_score=10.0  # 10点
    ),
    "DETAIL_RHETORIC": CriteriaInfo(
        id="DETAIL_RHETORIC",
        display_name="細部の修辞表現",
        priority=CRITERIA_PRIORITY["DETAIL_RHETORIC"],
        criteria_ids=["メッセージとボディの論理的整合性"],
        max_score=10.0  # 10点
    )
} 