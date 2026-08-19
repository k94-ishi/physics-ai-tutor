// Simple dictionary-based translations. Not a full i18n library - flat,
// dot-namespaced keys map directly to strings, with {placeholder}
// interpolation handled by LanguageContext's `t()`. `en` is typed against
// `keyof typeof ja` so adding a key to one side without the other is a
// compile error.

const ja = {
    // common
    "common.search": "検索",
    "common.searching": "検索中...",
    "common.searchFailed": "検索に失敗しました。",
    "common.delete": "削除",
    "common.cancel": "キャンセル",
    "common.edit": "編集",
    "common.history": "履歴",
    "common.approve": "承認",
    "common.reject": "却下",
    "common.loading": "読み込み中...",
    "common.processing": "処理中...",
    "common.retry": "再読み込み",
    "common.selectAll": "全選択",
    "common.selectedCount": "{count}件選択中",
    "common.all": "すべて",
    "common.keywordSearch": "キーワード検索",
    "common.move": "移動",
    "common.pageSize": "表示件数",
    "common.itemsUnit": "{count}件",
    "common.rangeSummary": "{start}–{end}件 / 全{total}件",
    "common.prevPage": "前のページ",
    "common.nextPage": "次のページ",
    "common.jumpToPage": "ページ番号を直接入力",

    // header
    "header.questionList": "質問一覧",
    "header.questionManagement": "質問管理",
    "header.userManagement": "ユーザー管理",
    "header.logout": "ログアウト",
    "header.adminLogin": "管理者ログイン",
    "header.logoutSuccess": "ログアウトしました。",
    "header.logoutFailed": "ログアウトに失敗しました。",

    // home
    "home.heading": "学習データベース",

    // questionList
    "questionList.modeAi": "AIに聞く-検索/生成",
    "questionList.keywordPlaceholder":
        "キーワードで質問・回答を絞り込み(スペース区切りでAND検索)",
    "questionList.searchInQuestion": "質問を検索対象にする",
    "questionList.searchInAnswer": "回答を検索対象にする",
    "questionList.fetchFailed": "質問を取得できませんでした。",
    "questionList.empty": "登録されている質問がありません。",

    // questionSearch (QuestionSearchAndAsk)
    "questionSearch.placeholder": "質問を入力すると意味が近い質問を検索します",
    "questionSearch.minLength": "{min}文字以上入力してください",
    "questionSearch.askPrompt": "以下に目的の質問はありませんか？",
    "questionSearch.askButton": "AIによる回答生成を実行",
    "questionSearch.noResults": "関連する質問が見つかりませんでした。",
    "questionSearch.topMatchBanner": "聞きたいのはこの質問ですか？",
    "questionSearch.relevance": "関連度",
    "questionSearch.generating": "回答を生成中...",
    "questionSearch.askFailed": "AIへの質問に失敗しました。",

    // questionDetail
    "questionDetail.alreadyAnswered": "この質問に対する回答はすでに生成済みです",
    "questionDetail.unreviewedBadge": "管理者未チェック",
    "questionDetail.relatedQuestions": "関連する質問",

    // askAiBox
    "askAiBox.heading": "AIに質問する",

    // referencedQuestions
    "referencedQuestions.heading": "回答生成時に参考にしたQA:",

    // login
    "login.email": "メールアドレス",
    "login.password": "パスワード",
    "login.invalidCredentials": "メールアドレスまたはパスワードが正しくありません。",
    "login.loggingIn": "ログイン中...",

    // admin (admin/questions/page.tsx only)
    "admin.status.unreviewed": "未レビュー",
    "admin.status.approved": "承認済み",
    "admin.status.rejected": "却下",
    "admin.confirmBulkDelete": "選択した質問を削除しますか？",
    "admin.confirmBulkApprove": "選択した質問を承認しますか？",
    "admin.confirmBulkReject": "選択した質問を却下しますか？",
    "admin.confirmBulkExtract": "選択した質問のConceptを抽出しますか？",
    "admin.extractLabel": "抽出",
    "admin.questionDeleted": "質問を削除しました。",
    "admin.questionDeleteFailed": "質問の削除に失敗しました。",
    "admin.questionApproved": "質問を承認しました。",
    "admin.questionRejected": "質問を却下しました。",
    "admin.actionFailed": "処理に失敗しました。",
    "admin.bulkDeletedCount": "{count}件を削除しました。",
    "admin.bulkApprovedCount": "{count}件を承認しました。",
    "admin.bulkRejectedCount": "{count}件を却下しました。",
    "admin.bulkActionFailed": "一括処理に失敗しました。",
    "admin.uploadJsonl": "JSONLアップロード",
    "admin.newQuestion": "新規登録",
    "admin.similaritySearchMode": "関連度検索",
    "admin.statusFilterLabel": "ステータスで絞り込み",
    "admin.conceptFilterLabel": "Concept状態で絞り込み",
    "admin.conceptExtracted": "抽出済み",
    "admin.conceptUnextracted": "未抽出",
    "admin.keywordPlaceholder": "キーワードで質問・回答を絞り込み",
    "admin.fetchFailed": "質問一覧を取得できませんでした。",
    "admin.noConceptMatch":
        "Concept状態の条件に一致する質問がこのページにはありません。",
    "admin.bulkApprove": "一括承認",
    "admin.bulkReject": "一括却下",
    "admin.extractConcepts": "Concept抽出",
    "admin.bulkDelete": "一括削除",
    "admin.selectQuestion": "{question}を選択",
    "admin.ragGenerated": "RAG生成",
    "admin.conceptsExtractedCount": "概念抽出済み({count})",
    "admin.conceptsNotExtracted": "概念未抽出",
    "admin.extractionProcessing": "Concept抽出: 処理中",
    "admin.extractionDone": "Concept抽出: 完了",
    "admin.extractionFailed": "Concept抽出: 失敗",
    "admin.approving": "承認中",
    "admin.rejecting": "却下中",
    "admin.approveFailed": "承認に失敗",
    "admin.rejectFailed": "却下に失敗",
    "admin.confirmDeleteQuestion": "質問を削除しますか？",
    "admin.bulkTargetCount": "{count}件が対象です。",
} as const;

const en: Record<keyof typeof ja, string> = {
    // common
    "common.search": "Search",
    "common.searching": "Searching...",
    "common.searchFailed": "Search failed.",
    "common.delete": "Delete",
    "common.cancel": "Cancel",
    "common.edit": "Edit",
    "common.history": "History",
    "common.approve": "Approve",
    "common.reject": "Reject",
    "common.loading": "Loading...",
    "common.processing": "Processing...",
    "common.retry": "Retry",
    "common.selectAll": "Select all",
    "common.selectedCount": "{count} selected",
    "common.all": "All",
    "common.keywordSearch": "Keyword Search",
    "common.move": "Go",
    "common.pageSize": "Rows per page",
    "common.itemsUnit": "{count}",
    "common.rangeSummary": "{start}–{end} of {total}",
    "common.prevPage": "Previous page",
    "common.nextPage": "Next page",
    "common.jumpToPage": "Jump to page",

    // header
    "header.questionList": "Questions",
    "header.questionManagement": "Manage Questions",
    "header.userManagement": "Manage Users",
    "header.logout": "Logout",
    "header.adminLogin": "Admin Login",
    "header.logoutSuccess": "Logged out.",
    "header.logoutFailed": "Failed to log out.",

    // home
    "home.heading": "Knowledge Base",

    // questionList
    "questionList.modeAi": "Ask AI - Search / Generate",
    "questionList.keywordPlaceholder":
        "Filter by keyword in question/answer (space-separated AND search)",
    "questionList.searchInQuestion": "Search in questions",
    "questionList.searchInAnswer": "Search in answers",
    "questionList.fetchFailed": "Failed to load questions.",
    "questionList.empty": "No questions found.",

    // questionSearch (QuestionSearchAndAsk)
    "questionSearch.placeholder": "Enter a question to search for similar ones",
    "questionSearch.minLength": "Please enter at least {min} characters",
    "questionSearch.askPrompt": "Don't see what you're looking for below?",
    "questionSearch.askButton": "Generate an AI Answer",
    "questionSearch.noResults": "No related questions found.",
    "questionSearch.topMatchBanner": "Is this the question you meant?",
    "questionSearch.relevance": "Relevance",
    "questionSearch.generating": "Generating answer...",
    "questionSearch.askFailed": "Failed to ask AI.",

    // questionDetail
    "questionDetail.alreadyAnswered":
        "An answer to this question has already been generated",
    "questionDetail.unreviewedBadge": "Not reviewed by admin",
    "questionDetail.relatedQuestions": "Related Questions",

    // askAiBox
    "askAiBox.heading": "Ask AI",

    // referencedQuestions
    "referencedQuestions.heading": "Referenced Q&A used to generate this answer:",

    // login
    "login.email": "Email",
    "login.password": "Password",
    "login.invalidCredentials": "Invalid email or password.",
    "login.loggingIn": "Logging in...",

    // admin (admin/questions/page.tsx only)
    "admin.status.unreviewed": "Unreviewed",
    "admin.status.approved": "Approved",
    "admin.status.rejected": "Rejected",
    "admin.confirmBulkDelete": "Delete the selected questions?",
    "admin.confirmBulkApprove": "Approve the selected questions?",
    "admin.confirmBulkReject": "Reject the selected questions?",
    "admin.confirmBulkExtract": "Extract concepts for the selected questions?",
    "admin.extractLabel": "Extract",
    "admin.questionDeleted": "Question deleted.",
    "admin.questionDeleteFailed": "Failed to delete question.",
    "admin.questionApproved": "Question approved.",
    "admin.questionRejected": "Question rejected.",
    "admin.actionFailed": "Action failed.",
    "admin.bulkDeletedCount": "{count} deleted.",
    "admin.bulkApprovedCount": "{count} approved.",
    "admin.bulkRejectedCount": "{count} rejected.",
    "admin.bulkActionFailed": "Bulk action failed.",
    "admin.uploadJsonl": "Upload JSONL",
    "admin.newQuestion": "New Question",
    "admin.similaritySearchMode": "Similarity Search",
    "admin.statusFilterLabel": "Filter by Status",
    "admin.conceptFilterLabel": "Filter by Concept Status",
    "admin.conceptExtracted": "Extracted",
    "admin.conceptUnextracted": "Not extracted",
    "admin.keywordPlaceholder": "Filter by keyword in question/answer",
    "admin.fetchFailed": "Failed to load the question list.",
    "admin.noConceptMatch":
        "No questions on this page match the concept filter.",
    "admin.bulkApprove": "Bulk Approve",
    "admin.bulkReject": "Bulk Reject",
    "admin.extractConcepts": "Extract Concepts",
    "admin.bulkDelete": "Bulk Delete",
    "admin.selectQuestion": "Select {question}",
    "admin.ragGenerated": "RAG Generated",
    "admin.conceptsExtractedCount": "Concepts extracted ({count})",
    "admin.conceptsNotExtracted": "Concepts not extracted",
    "admin.extractionProcessing": "Extracting concepts...",
    "admin.extractionDone": "Concepts extracted",
    "admin.extractionFailed": "Concept extraction failed",
    "admin.approving": "Approving...",
    "admin.rejecting": "Rejecting...",
    "admin.approveFailed": "Approval failed",
    "admin.rejectFailed": "Rejection failed",
    "admin.confirmDeleteQuestion": "Delete this question?",
    "admin.bulkTargetCount": "{count} selected.",
};

export const translations = { ja, en };
export type TranslationKey = keyof typeof ja;
