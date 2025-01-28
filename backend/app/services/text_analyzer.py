"""
テキスト解析を管理するサービス
"""
from typing import List, Dict, Any, Tuple

class TextAnalyzer:
    @staticmethod
    def analyze_document(full_text: str, summary: str, paragraphs: List[str], title: str) -> Tuple[Dict[str, str], List[str]]:
        """
        文書を解析し、各部分にタグを付与する
        
        Args:
            full_text (str): 文書全体のテキスト
            summary (str): サマリー部分
            paragraphs (List[str]): 段落リスト
            title (str): タイトル
            
        Returns:
            Tuple[Dict[str, str], List[str]]: 
                - タグ付けされた文書（{タグ: テキスト}）
                - 評価対象の文章リスト（順序保持）
        """
        tagged_sections = {}
        sentence_list = []
        
        # タイトルの処理
        if title.strip():
            tagged_sections["Title"] = title.strip()
            sentence_list.append(title.strip())
        
        # サマリーの処理
        summary_sentences = summary.split('。')
        for i, sent in enumerate(summary_sentences, 1):
            if sent.strip():
                tag = f"Summary{i}"
                tagged_sections[tag] = sent.strip()
                sentence_list.append(sent.strip())
        
        # パラグラフの処理
        story_count = 1
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # ストーリーとボディを区別
            if paragraph.startswith('・') or len(paragraph) < 50:  # ストーリーの判定基準
                tag = f"Story{story_count}"
                story_count += 1
                sentence_list.append(paragraph.strip())
            else:
                tag = f"Body{story_count-1}"
            
            tagged_sections[tag] = paragraph.strip()
        
        return tagged_sections, sentence_list

    @staticmethod
    def format_evaluation_result(tag: str, text: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        評価結果を指定された形式にフォーマット
        
        Args:
            tag (str): テキストのタグ
            text (str): 評価対象テキスト
            evaluation (Dict[str, Any]): 評価結果
            
        Returns:
            Dict[str, Any]: フォーマットされた評価結果
        """
        return {
            "tag": tag,
            "text": text,
            "evaluation": evaluation
        } 