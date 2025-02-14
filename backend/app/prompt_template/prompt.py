"""
評価用のプロンプトテンプレートを管理するモジュール
"""

SYSTEM_PROMPT = """
あなたは日本語の文章理解度評価の専門家です。
与えられた評価基準に基づいて文章を分析し、具体的なフィードバックを提供してください。
評価結果は必ずJSON形式で返してください。

評価結果のJSON形式は以下の通りです：
{
    "category": "評価カテゴリ名",
    "score": 評価スコア（0-1の小数）,
    "feedback": [
        "フィードバック1",
        "フィードバック2",
        ...
    ],
    "improvement_suggestions": [
        "改善提案1",
        "改善提案2",
        ...
    ],
    "target_sentence": "評価対象の文章"
}
"""

# 評価対象範囲の定義
EVALUATION_TARGETS = {
    "FULL_SUMMARY_AND_STORY": "full_summary_and_story",     # サマリーとストーリー全文
    "FULL_SUMMARY": "full_summary",                         # サマリー全文
    "CONSECUTIVE_SUMMARY": "consecutive_summary",           # 連続するサマリー
    "SUMMARY_STORY_BLOCK": "summary_story_block",          # サマリーとストーリーのブロック
    "SUMMARY_WISE_STORY_BLOCK": "summary_wise_story_block", # サマリごとのストーリーのブロック
    "STORY_WISE_BODY_BLOCK": "story_wise_body_block"       # ストーリーごとのボディのブロック
}

# 評価基準のプロンプトテンプレート
EVALUATION_CRITERIA_PROMPTS = {
    "最低限の修辞表現": {
        "role": "あなたは日本語の文章理解度評価の専門家です。",
        "purpose": "以下の制約条件に基づいて、指定された文章が日本語として意味が通じるかを評価し、文意が理解できない部分を報告してください。文意が理解できない部分がある場合は指定された形式で出力し、ない場合は「問題なし」と出力する。",
        "constraints": [
            "誤字脱字は無視する。",
            "大文字小文字の違いは無視する。",
            "単語レベルでわからない（英語の略語など）は、無視する。",
            "「以上のような」「前述の」などの前述の項目を指す表現が含まれていても、意味は通じるため、文意が理解できない理由にはしない。",
            "「xxx」「N」などの仮置きの数値や項目が含まれていても、意味は通じるため、文意が理解できない理由にはしない。"
        ],
        "thought_process": [
            "1. 入力された文章を注意深く読み、各文の意味を理解しようと試みる",
            "2. 理解できない文章を特定する",
            "3. 理解できない部分について、なぜ理解が難しいかを分析する",
            "4. なぜ理解が難しいかの理由が、制約条件のどれかに当てはまる場合は、「問題なし」と判断し直す",
            "5. 発見した問題を指定された形式でまとめる",
            "6. 問題がない場合は「問題なし」と判断する"
        ],
        "output_requirements": {
            "format": {
                "文意が理解できない場合": "｛文意が理解できない箇所：理解できない理由}",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "文意が理解できない部分のみを報告する",
                "誤字脱字や大文字小文字の違いは完全に無視する",
                "簡潔かつ明確に問題点を説明する",
                "可能な限り、文意が理解できない理由も簡単に説明する"
            ]
        },
        "final_instruction": "上記の指示に従って、提供された文章を評価し、日本語として文意が理解できない部分があればそれを報告してください。文意が十分に理解できる場合は、「問題なし」と報告してください。"
    },
    "前回の振り返りの有無": {
        "role": "あなたは戦略コンサルティングの専門家で、週次定例ミーティングに向けたストーリーの論理的な側面を評価する分析官です。",
        "purpose": "提供された複数のセンテンスを分析し、指定された評価基準に基づいて複数のセンテンスの質を評価し、改善が必要な点のみを指摘してください。",
        "constraints": [
            "評価基準を満たしている項目については言及しないでください。",
            "問題点が見つかった場合のみ、該当する評価項目を指摘してください。",
            "改善案の提示は不要です。問題点の指摘のみを行ってください。"
        ],
        "thought_process": [
            "1. 提供されたセンテンス群を全体的に確認し、構成を把握します",
            "2.提供されたセンテンス群が評価項目を満たしているかどうかを判断してください",
            "3. 評価項目を満たしていない場合、該当する評価項目を指摘してください"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください。",
                "専門家としての視点を維持し、客観的な評価を行ってください。",
            ]
        },
        "output_example": [
            "問題あり：全センテンスを通して「前回討議振り返り」または「背景・目的」に当たる内容がありません。"
        ],
        "vocabulary_definition": [
            "「前回討議振り返り」とは、前回までの討議内容を簡単に振り返る文章である。",
            "「背景・目的」は、踏まえての今回の議論の目的を整理した文章である。"
        ],
        "evaluation_items": [
            "1. 構成：全センテンスの中で、「前回討議振り返り」または「背景・目的」に対応する内容があるか。"
        ],
        "final_instruction": "提供されたセンテンス群を分析し、上記の評価項目に基づいて問題点のみを指摘してください。"
    },
    "SCQA有無": {
        "role": "あなたは戦略コンサルティングの専門家で、週次定例ミーティングに向けたストーリーの論理的な側面を評価する分析官です。",
        "purpose": "提供された複数のセンテンスを分析し、指定された評価基準に基づいて複数センテンスの質を評価し、改善が必要な点のみを指摘してください。",
        "constraints": [
            "評価基準を満たしている項目については言及しないでください。",
            "問題点が見つかった場合のみ、該当する評価項目を指摘してください。",
            "改善案の提示は不要です。問題点の指摘のみを行ってください。"
        ],
        "thought_process": [
            "1. 提供されたセンテンス群を全体的に確認し、構成を把握する",
            "2. 評価項目を、提供されたセンテンス群が満たしていない場合、該当する項目を記録し、問題点のみをまとめる",
            "3. ただしCは存在しない場合、またAが単文では記述されていない場合は「問題なし」と判断する"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください。",
                "専門家としての視点を維持し、客観的な評価を行ってください。"
            ]
        },
        "output_example": [
            "問題あり：全センテンスを通してSCQAのうちSに当たる内容がありません。"
        ],
        "vocabulary_definition": [
            "S: クライアントにとって既知の情報",
            "C: クライアントにとって新規の情報",
            "Q: 今回の討議で議論したい /認識を整合したい内容",
            "A: Qに対する回答や提案"
        ],
        "evaluation_items": [
            "1. SCQA構造：全センテンスの中に、S、C、Q、Aの要素が存在するか。"
        ],
        "final_instruction": "提供されたセンテンス群を分析し、上記の評価項目に基づいて問題点のみを指摘してください。評価項目をすべて満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "転換の接続詞の重複利用": {
        "role": "あなたは戦略コンサルティングの専門家で、週次定例ミーティングに向けたストーリーの論理的な側面を評価する分析官です。",
        "purpose": "提供された複数のセンテンスを分析し、指定された評価基準に基づいて複数センテンスの質を評価し、改善が必要な点のみを指摘してください。",
        "constraints": [
            "問題点が見つかった場合のみ、該当する評価項目を指摘してください",
            "改善案の提示は不要です。問題点の指摘のみを行ってください"
        ],
        "thought_process": [
            "1. 提供されたセンテンス群を全体的に確認し、構成を把握します。",
            "2. 評価項目を、提供されたセンテンス群が満たしていない場合、該当する項目を記録し、問題点のみをまとめます。"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：転換（しかし）の接続詞が文頭に用いられているセンテンスが全センテンス合わせて２文以上存在します。"
        ],
        "reference_for_evaluation_items": [
            "1. 付加（例：そして）",
            "2. 例示（例：例えば）",
            "3. 理由（例：なぜなら）",
            "4. 転換（例：しかし）",
            "5. 解説（例：つまり）",
            "6. 帰結（例：ゆえに、したがって）",
            "7. 補足（例：ただし）",
            "8. 並列（例：また）"
        ],
        "evaluation_items": [
            "1. 転換の適切性：文頭で転換（しかし）の接続詞が用いられているセンテンスが全センテンス合わせて２文以下か。"
        ],
        "final_instruction": "提供されたセンテンス群を分析し、上記の評価項目に基づいて問題点のみを指摘してください。評価項目をすべて満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "接続詞の妥当性": {
        "role": "あなたは戦略コンサルティングの専門家で、週次定例ミーティングに向けたストーリーの論理的な側面を評価する分析官です。",
        "purpose": "提供されたサマリーの文章を分析し、指定された評価基準に基づいて複数サマリー文の質を評価し、改善が必要な点のみを指摘してください。",
        "constraints": [
            "問題点が見つかった場合のみ、該当する評価項目を指摘してください",
            "改善案の提示は不要です。問題点の指摘のみを行ってください"
        ],
        "thought_process": [
            "1. 提供されたセンテンスを確認し、構成を把握します",
            "2. 評価項目に沿って、提供されたセンテンスを分析する",
            "3. 評価項目を満たしていない場合、該当する項目を記録する",
            "4. 最後に問題点のみをまとめます"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：市場シェアを拡大するためには、製品の品質向上も重要です：ひとつ前のサマリ文とは転換（逆説）の関係性だが、転換の接続詞が存在しない"
        ],
        "reference_for_evaluation_items": [
            "1. 理由（例：なぜなら）",
            "2. 転換（例：しかし、だが、一方で、ところが）",
            "3. 帰結（例：ゆえに、したがって）",
            "4. 補足：前文に対して補足的な情報を説明する場合。（例：ただし）",
            "5. 付加：前文に重要な情報を付加する。補足とは区別する（例：さらに）"
        ],
        "evaluation_items": [
            "1. 接続詞の適切性：本サマリー文の内容が、前サマリー文との内容と転換/帰結/補足/理由の関係性で、対応する転換/帰結/補足/理由を表す接続詞が存在するか。"
        ],
        "final_instruction": "提供されたサマリー文章を分析し、上記の評価項目に基づいて問題点のみを指摘してください。評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "サマリーレイヤーに不適な接続詞の有無": {
        "role": "あなたは戦略コンサルティングの専門家で、週次定例ミーティングに向けたストーリーの論理的な側面を評価する分析官です。",
        "purpose": "提供されたサマリーの文章を分析し、指定された評価基準に基づいて複数サマリー文の質を評価し、改善が必要な点のみを指摘してください。",
        "constraints": [
            "問題点が見つかった場合のみ、該当する評価項目を指摘してください",
            "改善案の提示は不要です。問題点の指摘のみを行ってください"
        ],
        "thought_process": [
            "1. 提供されたサマリー文を全体的に確認し、構成を把握します",
            "2. 評価項目に沿って、提供されたサマリー文を分析する",
            "3. 評価項目を満たしていない場合、該当する項目を記録する",
            "4. 最後に問題点のみをまとめまる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：例えば、品質管理プロセスの見直しと顧客フィードバックの積極的な活用が考えられます：例示の接続詞が利用されています。"
        ],
        "reference_for_evaluation_items": [
            "1. 例示（例：例えば）",
            "2. 解説（例：つまり）"
        ],
        "evaluation_items": [
            "1. 接続詞の使用制限：各サマリー文の文頭に、例示、解説の接続詞が用いられていないか。"
        ],
        "final_instruction": "提供されたサマリー文を分析し、上記の評価項目に基づいて問題点のみを指摘してください。評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "直前のサマリーとの論理的連続性": {
        "role": "あなたは戦略コンサルティングの専門家で、週次定例ミーティングに向けたストーリーの論理的な側面を評価する分析官です。",
        "purpose": "提供されたサマリーの文章を分析し、指定された評価基準に基づいて複数サマリー文の質を評価し、改善が必要な点のみを指摘してください。",
        "constraints": [
            "問題点が見つかった場合のみ、該当する評価項目を指摘してください",
            "改善案の提示は不要です。問題点の指摘のみを行ってください"
        ],
        "thought_process": [
            "1. 提供されたサマリー文を確認し、構成を把握します",
            "2. 評価項目に沿って、提供されたサマリー文を分析する",
            "3. 評価項目を満たしていない場合、該当する項目を記録する",
            "4. 最後に問題点のみをまとめまる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：しかし、市場シェアを拡大するためには、製品の品質向上も重要です：直前の文章から、内容や論理が飛躍しています。"
        ],
        "evaluation_items": [
            "1. 論理的連続性：各文が、直前の文から自然に続く内容になっているか、急な話題の変更や飛躍した内容になっていないか。"
        ],
        "final_instruction": "提供されたサマリー文を分析し、上記の評価項目に基づいて問題点のみを指摘してください。評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "メッセージレイヤーの逐次的展開性": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "提供された単一のサマリーセンテンスと複数のメッセージセンテンスを評価し、指定された評価項目に基づいて、改善が必要な問題点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. サマリーセンテンス及びメッセージセンテンスを注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて分析を行う",
            "3. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：サマリーには「点群データによる3Dモデル生成」との比較が明示されているが、メッセージ内にはこの「点群データ」に言及がないため、サマリーの内容が論理的に導出できません。"
        ],
        "evaluation_items": [
            "※それぞれのメッセージセンテンス単体の内容は、論証する必要がなく自明とする。",
            "1. メッセージセンテンス間のつながりに矛盾はないか。",
            "2. メッセージセンテンスからサマリ―センテンスを導出する際に、論理的な推論で導出できているか。",
            "3. メッセージセンテンスからサマリ―センテンスを導出する際に、論理的な誤りや誤謬が含まれていないか。"
        ],
        "final_instruction": "上記の指示に従って、提供されたメッセージセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。それぞれのメッセージセンテンス単体の内容は、論証する必要がなく自明とする。"
    },
    "逐次的展開の評価": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "提供された複数のストーリーセンテンスを評価し、指定された評価項目に基づいて、改善が必要な点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. サマリーセンテンス及びストーリーセンテンスを注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて分析を行う",
            "3. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：サマリーには「点群データによる3Dモデル生成」との比較が明示されているが、ストーリー内にはこの「点群データ」に言及がないため、サマリーの内容が論理的に導出できません。"
        ],
        "evaluation_items": [
            "1. ストーリ―センテンス間で内容に矛盾はないか。",
            "2. ストーリ―センテンスからサマリーセンテンスを導出するために、ストーリーセンテンス以外の追加の情報は必要ないか。",
            "3. ストーリーセンテンスからサマリ―センテンスを導出する際に、論理的な推論で導出できているか。",
            "4. ストーリーセンテンスからサマリ―センテンスを導出する際に、論理的な誤りや誤謬が含まれていないか。"
        ],
        "final_instruction": "上記の指示に従って、提供されたストーリーセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "根拠s, 詳細s⇔主張": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "提供された単一のサマリーセンテンスと複数のメッセージセンテンスを評価し、指定された評価項目に基づいて、改善が必要な問題点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. サマリーセンテンス及びメッセージセンテンスを注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて分析を行う",
            "3. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：サマリーには「点群データによる3Dモデル生成」との比較が明示されているが、メッセージ内にはこの「点群データ」に言及がないため、サマリーの内容が論理的に導出できません。"
        ],
        "evaluation_items": [
            "※それぞれのメッセージセンテンス単体の内容は、論証する必要がなく自明とする。",
            "1. メッセージセンテンスからサマリ―センテンスを導出する際に、論理的な推論で導出できているか。",
            "2. メッセージセンテンスからサマリ―センテンスを導出する際に、論理的な推論で導出できているか。"
        ],
        "final_instruction": "上記の指示に従って、提供されたサマリーセンテンスとメッセージセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。それぞれのメッセージセンテンス単体の内容は、論証する必要がなく自明とする。"
    },
    "接続詞の適切性": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "提供された複数のストーリーセンテンスを評価し、指定された評価項目に基づいて、改善が必要な点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. サマリーセンテンス及びストーリーセンテンスを注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて分析を行う",
            "3. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：サマリーには「点群データによる3Dモデル生成」との比較が明示されているが、ストーリー内にはこの「点群データ」に言及がないため、サマリーの内容が論理的に導出できません。"
        ],
        "evaluation_items": [
            "1. ストーリ―センテンス間で内容に矛盾はないか。",
            "2. ストーリ―センテンスからサマリーセンテンスを導出するために、ストーリーセンテンス以外の追加の情報は必要ないか。",
            "3. ストーリーセンテンスからサマリ―センテンスを導出する際に、論理的な推論で導出できているか。",
            "4. ストーリーセンテンスからサマリ―センテンスを導出する際に、論理的な誤りや誤謬が含まれていないか。"
        ],
        "final_instruction": "上記の指示に従って、提供されたストーリーセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "転換の接続詞の二重利用": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "複数のメッセージセンテンスを評価し、指定された評価項目に基づいて、改善が必要な点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. メッセージセンテンスを一つ一つ注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて、一メッセージメッセージずつ分析を行う",
            "3. 問題点が見つかった場合、該当するメッセージセンテンスと問題点を記録する",
            "4. すべてのメッセージについて確認を終えた後、該当メッセージセンテンスと問題点のリストを作成する",
            "5. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：しかし、市場シェアを拡大するためには、製品の品質向上も重要です；　転換の接続詞がメッセージ郡で２回以上利用されています。"
        ],
        "reference_for_evaluation_items": [
            "1. 付加（例：そして）",
            "2. 例示（例：例えば）",
            "3. 理由（例：なぜなら）",
            "4. 転換（例：しかし）",
            "5. 解説（例：つまり）",
            "6. 帰結（例：ゆえに、したがって）",
            "7. 補足（例：ただし）",
            "8. 並列（例：また）"
        ],
        "evaluation_items": [
            "1. 転換接続詞の過剰使用：メッセージセンテンス群の文頭に、転換の接続詞が2回以上出てきていないか。"
        ],
        "final_instruction": "上記の指示に従って、提供されたメッセージセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるメッセージセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "無駄なナンバリングの回避": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "複数のメッセージセンテンスを評価し、指定された評価項目に基づいて、改善が必要な点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. メッセージセンテンスを一つ一つ注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて、メッセージ全体の分析を行う",
            "3. 問題点が見つかった場合、該当するメッセージセンテンスと問題点を記録する",
            "4. 行動やネクストアクションのナンバリングを行っている場合は、後述されていなくても問題なし",
            "5. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：今度アパレル企業A社が進出する新興国の候補として、三つありインド、ベトナム、フィリピンである。；該当メッセージで対象を構造化して整理しているにもかかわらず、後続のメッセージで構造化された要素に関して言及していない。"
        ],
        "evaluation_items": [
            "1. 構造化の一貫性：あるメッセージセンテンスで対象をナンバリング（例：「xxxのステップは3段階あり、ABCです。」）した場合、後続のメッセージセンテンスでそれらについて言及されているか。",
            "※1. 言及の方法は、「Aはxxx, Bはxxxである」などの直接的な言及でも良いし、「それらステップはxxxである」、というような言及の仕方でも良い。",
            "※2. 行動やネクストアクションのナンバリングを行っている場合は、後述されていなくても問題なし。"
        ],
        "final_instruction": "上記の指示に従って、提供されたメッセージセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるメッセージセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。"
    },
    "メッセージとボディの論理的整合性": {
        "role": "あなたは戦略コンサルティングの専門家であり、ストーリーテリングと論理構成の評価者です。",
        "purpose": "提供された単一のメッセージセンテンスと複数のボディセンテンスを評価し、指定された評価項目に基づいて、改善が必要な問題点を特定することです。",
        "constraints": [
            "評価は客観的かつ公平に行う",
            "指定された評価項目のみを使用する",
            "問題点が見つかった場合のみ、該当する評価項目と問題のあるセンテンスを出力する",
            "評価結果は簡潔かつ明確に提示する"
        ],
        "thought_process": [
            "1. メッセージセンテンス及びボディセンテンスを注意深く読み、全体の構造を把握する",
            "2. 評価項目に基づいて分析を行う",
            "3. 最終的な評価結果をまとめる"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "制約条件を厳守し、問題点のみを簡潔に指摘してください",
                "専門家としての視点を維持し、客観的な評価を行ってください"
            ]
        },
        "output_example": [
            "問題あり：メッセージには「点群データによる3Dモデル生成」との比較が明示されているが、ボディ内にはこの「点群データ」に言及がないため、メッセージの内容が論理的に導出できません。"
        ],
        "evaluation_items": [
            "※それぞれのボディセンテンス単体の内容は、論証する必要がなく自明とする。",
            "1. ボディセンテンスからメッセージセンテンスを導出する際に、論理的な推論で導出できているか。",
            "2. ボディセンテンスからセンテンスセンテンスを導出する際に、論理的な誤りや誤謬が含まれていないか。"
        ],
        "final_instruction": "上記の指示に従って、提供されたメッセージセンテンスとボディセンテンスを評価し、問題点がある場合のみ、該当する評価項目と問題のあるセンテンスを指定されたフォーマットで出力してください。すべての評価項目を満たしている場合は、その旨を簡潔に伝えてください。それぞれのボディセンテンス単体の内容は、論証する必要がなく自明とする。"
    },
    "修辞表現": {
        "role": "あなたは戦略コンサルティングの言語表現と品質管理の専門家です。",
        "purpose": "提供されたミーティングのストーリーを評価し、特定の基準に基づいて問題点を指摘することです。",
        "constraints": [
            "評価基準を満たしていない場合のみ、問題点を指摘すること",
            "指摘する際は、該当する評価項目と問題のあるセンテンスを明確に示すこと",
            "「xxx」「N」などの仮置きの数値や項目が含まれて文意が曖昧になっている場合、これは「問題なし」とみなす",
            "基準を満たしている場合は、特に問題がない旨を簡潔に伝えること。"
        ],
        "thought_process": [
            "1. 修入力されたストーリーのセンテンスを分析する",
            "2. 各センテンスが、a)礼儀正しい日本語表現となっているか、b)表現の洗練度が高いか、を確認する",
            "3. 問題点が見つかった場合、該当する評価項目と問題のあるセンテンスを記録して、問題点のリストを作成する"
        ],
        "output_requirements": {
            "format": {
                "問題点がある場合のみ、次の形式で出力してください。他の要素の出力はしないでください。：": "問題あり：問題内容",
                "問題がない場合": "問題なし"
            },
            "guidelines": [
                "具体的かつ建設的な改善提案を行うこと",
                "指摘は客観的で公平であること",
                "専門用語を使用する場合は、必要に応じて簡単な説明を加えること"
            ]
        },
        "output_example": [
            " ｛「この改善は簡単に実施できるはずです。」：礼儀正しい表現に欠ける。「この改善案は、皆様のご協力のもと、効果的に実施できると考えております。」と改善}"
        ],
        "evaluation_items": [
            "1. 礼儀正しい表現：失礼な日本語表現になっていないか。(1-a~1-gは失礼な表現の例である)",
            "1-a. 「簡単に」「容易に」など、相手の努力を軽視する表現",
            "1-b. 「遅れている」「劣っている」など、否定的な評価を直接的に述べる表現",
            "1-c. 「失敗」「間違い」など、ネガティブな印象を与える言葉",
            "1-d. 「当然」「明らかに」など、相手の認識を決めつける表現",
            "1-e. 「～してください」という直接的な指示（代わりに「～していただけますと幸いです」などの丁寧な表現を使用）",
            "1-f. 「私が提案した通りに」など、自己中心的な表現",
            "1-g. 「常識的に考えて」など、相手の判断力を軽視する表現",
            "2. 明確な表現：人によって解釈が変わる単語を利用していないか。(2-a~2-fは人によって解釈が変わる単語の例である)",
            "2-a. 「非常に」「劇的に」「とても」など、定性的な強調表現",
            "2-b. 「適切な」「妥当な」「十分な」など、基準が不明確な形容詞",
            "2-c. 「早期に」「迅速に」「効率的に」など、具体的な時間や方法が示されていない副詞",
            "2-d. 「検討する」「考慮する」「整理する」など、具体的なアクションが不明確な動詞",
            "2-e. 「戦略的」「革新的」「最適化」など、具体的な意味が文脈によって変わる可能性のある形容詞",
            "2-f. 「プロセス」「フレームワーク」など、具体的な内容が不明確な名詞",
        ],
        "final_instruction": "上記の指示に従って、入力されたストーリーを評価し、問題点がある場合のみ指摘してください。すべての基準を満たしている場合は、その旨を簡潔に伝えてください。"
    }
}

# 評価基準のテンプレート
EVALUATION_CRITERIA = [
    {
        "name": "最低限の修辞表現",
        "description": "文章全体の基本的な修辞表現を評価します。",
        "max_score": 7.0,
        "priority": 1,
        "applicable_to": ["FULL_SUMMARY_AND_STORY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["最低限の修辞表現"]
    },
    {
        "name": "前回の振り返りの有無",
        "description": "前回の討議内容の振り返りが適切に含まれているかを評価します。",
        "max_score": 8.0,
        "priority": 2,
        "applicable_to": ["FULL_SUMMARY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["前回の振り返りの有無"]
    },
    {
        "name": "SCQA有無",
        "description": "SCQA形式が適切に使用されているかを評価します。",
        "max_score": 8.0,
        "priority": 3,
        "applicable_to": ["FULL_SUMMARY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["SCQA有無"]
    },
    {
        "name": "転換の接続詞の重複利用",
        "description": "転換を示す接続詞の重複使用を評価します。",
        "max_score": 7.0,
        "priority": 4,
        "applicable_to": ["FULL_SUMMARY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["転換の接続詞の重複利用"]
    },
    {
        "name": "接続詞の妥当性",
        "description": "接続詞の使用が文脈に適しているかを評価します。",
        "max_score": 7.0,
        "priority": 5,
        "applicable_to": ["CONSECUTIVE_SUMMARY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["接続詞の妥当性"]
    },
    {
        "name": "サマリーレイヤーに不適な接続詞の有無",
        "description": "サマリーレベルで不適切な接続詞の使用を評価します。",
        "max_score": 7.0,
        "priority": 6,
        "applicable_to": ["CONSECUTIVE_SUMMARY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["サマリーレイヤーに不適な接続詞の有無"]
    },
    {
        "name": "直前のサマリーとの論理的連続性",
        "description": "前のサマリーとの論理的なつながりを評価します。",
        "max_score": 7.0,
        "priority": 7,
        "applicable_to": ["CONSECUTIVE_SUMMARY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["直前のサマリーとの論理的連続性"]
    },
    {
        "name": "メッセージレイヤーの逐次的展開性",
        "description": "メッセージの論理的な展開を評価します。",
        "max_score": 7.0,
        "priority": 8,
        "applicable_to": ["SUMMARY_STORY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["メッセージレイヤーの逐次的展開性"]
    },
    {
        "name": "逐次的展開の評価",
        "description": "文章の展開の適切性を評価します。",
        "max_score": 7.0,
        "priority": 9,
        "applicable_to": ["SUMMARY_STORY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["逐次的展開の評価"]
    },
    {
        "name": "根拠s, 詳細s⇔主張",
        "description": "根拠や詳細から主張への論理的つながりを評価します。",
        "max_score": 7.0,
        "priority": 10,
        "applicable_to": ["SUMMARY_STORY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["根拠s, 詳細s⇔主張"]
    },
    {
        "name": "接続詞の適切性",
        "description": "ストーリー内での接続詞の使用が適切かを評価します。",
        "max_score": 7.0,
        "priority": 11,
        "applicable_to": ["SUMMARY_WISE_STORY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["接続詞の適切性"]
    },
    {
        "name": "転換の接続詞の二重利用",
        "description": "ストーリー内での転換を示す接続詞の重複使用を評価します。",
        "max_score": 7.0,
        "priority": 12,
        "applicable_to": ["SUMMARY_WISE_STORY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["転換の接続詞の二重利用"]
    },
    {
        "name": "無駄なナンバリングの回避",
        "description": "不必要なナンバリングの使用を評価します。",
        "max_score": 7.0,
        "priority": 13,
        "applicable_to": ["SUMMARY_WISE_STORY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["無駄なナンバリングの回避"]
    },
    {
        "name": "メッセージとボディの論理的整合性",
        "description": "メッセージとボディの論理的整合性を評価します。",
        "max_score": 7.0,
        "priority": 14,
        "applicable_to": ["STORY_WISE_BODY_BLOCK"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["メッセージとボディの論理的整合性"]
    },
    {
        "name": "修辞表現",
        "description": "文章全体の修辞表現の質を評価します。",
        "max_score": 7.0,
        "priority": 15,
        "applicable_to": ["FULL_SUMMARY_AND_STORY"],
        "prompt": EVALUATION_CRITERIA_PROMPTS["修辞表現"]
    }
]

# 評価プロンプトのテンプレート
EVALUATION_PROMPT_TEMPLATE = """
{description}

評価対象範囲：{target_type}

評価結果は以下の形式で返してください：
{{
    "category": "{name}",
    "score": スコア（0-1の数値）,
    "target_sentence": "評価対象の文章",
    "feedback": [
        "フィードバック1",
        "フィードバック2",
        ...
    ],
    "improvement_suggestions": [
        "改善提案1",
        "改善提案2",
        ...
    ]
}}

評価対象テキスト：
{text}
"""

def get_evaluation_text(document_structure: dict, target_type: str) -> str:
    """
    評価対象範囲に応じたテキストを取得する
    
    Args:
        document_structure (dict): 文書構造を表す辞書
        target_type (str): 評価対象範囲の種類
    
    Returns:
        str: 評価対象テキスト
    """
    try:
        text_parts = []
        
        if target_type == "FULL_SUMMARY_AND_STORY":
            # サマリーとストーリーを順番に結合
            summaries = document_structure.get("structure", {}).get("summary", [])
            stories = document_structure.get("structure", {}).get("story", [])
            
            for i, summary in enumerate(summaries):
                text_parts.append(f"【サマリー】\n{summary.strip()}")
                # 対応するストーリーを追加
                story_start = i * 2  # 仮定：各サマリーに2つのストーリーが対応
                story_end = (i + 1) * 2
                for story in stories[story_start:story_end]:
                    text_parts.append(f"【ストーリー】\n{story.strip()}")
                    
        elif target_type == "FULL_SUMMARY":
            # サマリーのみをまとめて評価
            summaries = document_structure.get("structure", {}).get("summary", [])
            for summary in summaries:
                text_parts.append(f"【サマリー】\n{summary.strip()}")
                
        elif target_type == "CONSECUTIVE_SUMMARY":
            # 連続するサマリーのペアを評価
            summaries = document_structure.get("structure", {}).get("summary", [])
            for i in range(1, len(summaries)):
                text_parts.append(f"【前のサマリー】\n{summaries[i-1].strip()}")
                text_parts.append(f"【現在のサマリー】\n{summaries[i].strip()}")
                
        elif target_type == "SUMMARY_STORY_BLOCK":
            # サマリーとその配下のストーリーをブロックとして評価
            summaries = document_structure.get("structure", {}).get("summary", [])
            stories = document_structure.get("structure", {}).get("story", [])
            
            for i, summary in enumerate(summaries):
                text_parts.append(f"【サマリー】\n{summary.strip()}")
                story_start = i * 2  # 仮定：各サマリーに2つのストーリーが対応
                story_end = (i + 1) * 2
                text_parts.append("【関連ストーリー】")
                for story in stories[story_start:story_end]:
                    text_parts.append(f"【ストーリー】{story.strip()}")
                    
        elif target_type == "SUMMARY_WISE_STORY_BLOCK":
            # サマリー配下のストーリー群を評価
            stories = document_structure.get("structure", {}).get("story", [])
            for i in range(0, len(stories), 2):  # 仮定：各サマリーに2つのストーリーが対応
                text_parts.append(f"【ストーリー群】")
                for story in stories[i:i+2]:
                    text_parts.append(f"【ストーリー】{story.strip()}")
                
        elif target_type == "STORY_WISE_BODY_BLOCK":
            # ストーリーとその配下のボディを評価
            stories = document_structure.get("structure", {}).get("story", [])
            bodies = document_structure.get("structure", {}).get("body", [])
            
            for i, story in enumerate(stories):
                text_parts.append(f"【ストーリー】\n{story.strip()}")
                if i < len(bodies):
                    text_parts.append("【関連ボディ】")
                    for body in bodies[i:i+1]:
                        text_parts.append(f"【ボディ】{body.strip()}")
        
        return "\n\n".join(text_parts)
        
    except Exception as e:
        logging.error(f"評価対象テキストの取得中にエラー: {str(e)}")
        return ""

def identify_target_type(document_structure: dict) -> str:
    """
    文書構造から評価対象範囲を識別する
    
    Args:
        document_structure (dict): 文書構造を表す辞書
    
    Returns:
        str: 評価対象範囲の種類（EVALUATION_TARGETSのキーのいずれか）
    """
    structure = document_structure.get("structure", {})
    has_summary = bool(structure.get("summary", []))
    has_story = bool(structure.get("story", []))
    has_body = bool(structure.get("body", []))
    
    if has_summary and has_story:
        return "FULL_SUMMARY_AND_STORY"
    elif has_summary:
        return "FULL_SUMMARY"
    elif has_story and has_body:
        return "STORY_WISE_BODY_BLOCK"
    else:
        raise ValueError("Invalid document structure")

def get_applicable_criteria(target_type):
    """
    指定された評価対象範囲に適用可能な評価基準を取得する
    
    Args:
        target_type (str): 評価対象範囲の種類
        
    Returns:
        list: 適用可能な評価基準のリスト
    """
    return [
        criterion for criterion in EVALUATION_CRITERIA
        if target_type in criterion.get("applicable_to", [])
    ]

def generate_evaluation_prompt(document_structure):
    """
    文書構造に応じた評価プロンプトを生成する
    
    Args:
        document_structure (dict): 文書構造を表す辞書
    
    Returns:
        list: 評価プロンプトのリスト
    """
    target_type = identify_target_type(document_structure)
    evaluation_text = get_evaluation_text(document_structure, target_type)
    applicable_criteria = get_applicable_criteria(target_type)
    
    prompts = []
    for criterion in applicable_criteria:
        prompt = EVALUATION_PROMPT_TEMPLATE.format(
            description=criterion["description"],
            name=criterion["name"],
            target_type=EVALUATION_TARGETS[target_type],
            text=evaluation_text
        )
        prompts.append({
            "prompt": prompt,
            "priority": criterion["priority"]
        })
    
    return prompts 