"""ソラ先生 会話返答（generate_reply）ハルシネーション/不自然日本語 自動検出eval。

docs/64_テスト計画_ソラ先生ハルシネーション自動検出eval.md に基づく。
本物の backend/app/coaching/llm.generate_reply() を実 Gemini で叩き、
決定論チェック（本モジュール）＋LLM審査（Workflow側）で所見を集める。
"""
