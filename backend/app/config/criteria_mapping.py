"""
評価基準のマッピングを定義するモジュール
"""
from dataclasses import dataclass
from typing import List

@dataclass
class CriteriaInfo:
    """評価カテゴリの情報を保持するクラス"""
    display_name: str
    priority: int
    criteria_ids: List[str]
    applicable_to: List[str]

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
        display_name="全文修辞表現",
        priority=CRITERIA_PRIORITY["FULL_TEXT_RHETORIC"],
        criteria_ids=["サマリとストーリーの日本語評価", "転換の接続詞チェック"],
        applicable_to=["FULL_DOCUMENT"]
    ),
    "SUMMARY_LOGIC_FLOW": CriteriaInfo(
        display_name="サマリーの論理展開",
        priority=CRITERIA_PRIORITY["SUMMARY_LOGIC_FLOW"],
        criteria_ids=["前回討議振り返り評価", "SCQA"],
        applicable_to=["SUMMARY_ONLY"]
    ),
    "SUMMARY_INTERNAL_LOGIC": CriteriaInfo(
        display_name="サマリー単体の論理",
        priority=CRITERIA_PRIORITY["SUMMARY_INTERNAL_LOGIC"],
        criteria_ids=["接続詞と内容の一致", "不適切な接続詞", "論理的連続性"],
        applicable_to=["SUMMARY_ONLY"]
    ),
    "SUMMARY_STORY_LOGIC": CriteriaInfo(
        display_name="サマリーとストーリー間の論理",
        priority=CRITERIA_PRIORITY["SUMMARY_STORY_LOGIC"],
        criteria_ids=["ストーリーの逐次的展開の評価", "逐次的展開", "根拠s, 詳細s⇒主張"],
        applicable_to=["SUMMARY_AND_STORY"]
    ),
    "STORY_INTERNAL_LOGIC": CriteriaInfo(
        display_name="ストーリー単体の論理",
        priority=CRITERIA_PRIORITY["STORY_INTERNAL_LOGIC"],
        criteria_ids=["接続詞の適切性", "転換接続詞の重複利用", "無駄なナンバリングの評価"],
        applicable_to=["STORY_AND_BODY"]
    ),
    "DETAIL_RHETORIC": CriteriaInfo(
        display_name="細部の修辞表現",
        priority=CRITERIA_PRIORITY["DETAIL_RHETORIC"],
        criteria_ids=["修辞評価"],
        applicable_to=["FULL_DOCUMENT"]
    )
} 