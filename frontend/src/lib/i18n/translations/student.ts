// Student pages: list, search, question page, tags ([64]).

export const ja = {
    "questionList.modeAi": "AIに聞く-検索/生成",
    "questionList.keywordPlaceholder":
        "キーワードで質問・回答を絞り込み(スペース区切りでAND検索)",
    "questionList.searchInQuestion": "質問を検索対象にする",
    "questionList.searchInAnswer": "回答を検索対象にする",
    "questionList.fetchFailed": "質問を取得できませんでした。",
    "questionList.empty": "登録されている質問がありません。",
    "questionSearch.placeholder": "質問を入力すると意味が近い質問を検索します",
    "questionSearch.minLength": "{min}文字以上入力してください",
    "questionSearch.askPrompt": "以下に目的の質問はありませんか？",
    "questionSearch.askButton": "AIによる回答生成を実行",
    "questionSearch.noResults": "関連する質問が見つかりませんでした。",
    "questionSearch.topMatchBanner": "聞きたいのはこの質問ですか？",
    "questionSearch.relevance": "関連度",
    "questionSearch.generating": "回答を生成中...",
    "questionSearch.askFailed": "AIへの質問に失敗しました。",
    "questionSearch.answerUnreviewed":
        "このAI回答はまだ先生のチェックを受けていません。",
    "questionSearch.cachedNotice": "同じ質問への以前の回答を表示しています。",
    "questionDetail.alreadyAnswered":
        "この質問に対する回答はすでに生成済みです",
    "questionDetail.unreviewedBadge": "管理者未チェック",
    "questionDetail.relatedQuestions": "関連する質問",
    "questionDetail.autoTranslated": "自動翻訳",
    "questionDetail.autoTranslatedReviewed": "レビュー済みの内容を自動翻訳",
    "askAiBox.heading": "AIに質問する",
    "referencedQuestions.heading": "回答生成時に参考にしたQA:",
    "questionPreview.openFull": "この質問のページを開く",
    "questionDetail.showMoreRelated": "関連する質問をもっと見る",
    "prerequisites.heading": "先に読むとよい質問",
    "prerequisites.hint":
        "この回答が使っているタグを、より基本的なところから説明している質問です。",
    "prerequisites.gapsLabel":
        "まだ説明する質問がないタグ(押すと、そのタグについて質問できます):",
    "prerequisites.gapTitle": "「{concept}」について質問する",
    "questionDetail.relatedHint":
        "カードを押すと、このページを離れずに中身を見られます。",
    "concepts.listLabel": "タグ",
    "concepts.chipTitle": "タグ「{concept}」の質問を見る",
    "concepts.showMore": "ほか{count}件",
    "concepts.filterBanner": "タグ「{concept}」の質問",
    "concepts.clearFilter": "絞り込みを解除",
    "concepts.noMatch":
        "タグ「{concept}」の公開済みの質問はまだありません。下から質問してみてください。",
    "conceptFilter.meanings":
        "タグ「{word}」には複数の意味があります。どれを見ますか?",
    "myQuestions.title": "自分の質問",
    "myQuestions.fetchFailed": "質問履歴を取得できませんでした。",
    "myQuestions.empty":
        "まだ質問の履歴がありません。ログインした状態でAIに質問すると、ここに記録されます。",
    "myQuestions.askedOn": "質問日",
    "myQuestions.rejectedNotice":
        "この回答は先生の確認により取り下げられました。もう一度質問し直してみてください。",
    "myQuestions.viewDetail": "詳細を見る",
} as const;

export const en: Record<keyof typeof ja, string> = {
    "questionList.modeAi": "Ask AI - Search / Generate",
    "questionList.keywordPlaceholder":
        "Filter by keyword in question/answer (space-separated AND search)",
    "questionList.searchInQuestion": "Search in questions",
    "questionList.searchInAnswer": "Search in answers",
    "questionList.fetchFailed": "Failed to load questions.",
    "questionList.empty": "No questions found.",
    "questionSearch.placeholder": "Enter a question to search for similar ones",
    "questionSearch.minLength": "Please enter at least {min} characters",
    "questionSearch.askPrompt": "Don't see what you're looking for below?",
    "questionSearch.askButton": "Generate an AI Answer",
    "questionSearch.noResults": "No related questions found.",
    "questionSearch.topMatchBanner": "Is this the question you meant?",
    "questionSearch.relevance": "Relevance",
    "questionSearch.generating": "Generating answer...",
    "questionSearch.askFailed": "Failed to ask AI.",
    "questionSearch.answerUnreviewed":
        "This AI answer has not been checked by a teacher yet.",
    "questionSearch.cachedNotice":
        "Showing a previous answer to the same question.",
    "questionDetail.alreadyAnswered":
        "An answer to this question has already been generated",
    "questionDetail.unreviewedBadge": "Not reviewed by admin",
    "questionDetail.relatedQuestions": "Related Questions",
    "questionDetail.autoTranslated": "Auto-translated",
    "questionDetail.autoTranslatedReviewed":
        "Auto-translated from reviewed content",
    "askAiBox.heading": "Ask AI",
    "referencedQuestions.heading":
        "Referenced Q&A used to generate this answer:",
    "questionPreview.openFull": "Open this question",
    "questionDetail.showMoreRelated": "Show more related questions",
    "prerequisites.heading": "Read these first",
    "prerequisites.hint":
        "Questions that explain the tags this answer relies on, starting lower.",
    "prerequisites.gapsLabel":
        "Tags with no explaining question yet (tap one to ask about it):",
    "prerequisites.gapTitle": 'Ask about "{concept}"',
    "questionDetail.relatedHint":
        "Tap a card to read it without leaving this page.",
    "concepts.listLabel": "Tags",
    "concepts.chipTitle": 'See questions tagged "{concept}"',
    "concepts.showMore": "{count} more",
    "concepts.filterBanner": 'Questions tagged "{concept}"',
    "concepts.clearFilter": "Clear filter",
    "concepts.noMatch":
        'No published question tagged "{concept}" yet. Try asking one below.',
    "conceptFilter.meanings":
        'The tag "{word}" has several meanings. Which one?',
    "myQuestions.title": "My questions",
    "myQuestions.fetchFailed": "Failed to load your question history.",
    "myQuestions.empty":
        "No question history yet. Questions you ask the AI while signed in are recorded here.",
    "myQuestions.askedOn": "Asked",
    "myQuestions.rejectedNotice":
        "This answer was withdrawn after a teacher's check. Please try asking again.",
    "myQuestions.viewDetail": "View details",
};
