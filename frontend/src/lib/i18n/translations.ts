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
    "header.login": "ログイン",
    "header.account": "アカウント",
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
    "questionSearch.answerUnreviewed":
        "このAI回答はまだ先生のチェックを受けていません。",
    "questionSearch.cachedNotice": "同じ質問への以前の回答を表示しています。",

    // questionDetail
    "questionDetail.alreadyAnswered": "この質問に対する回答はすでに生成済みです",
    "questionDetail.unreviewedBadge": "管理者未チェック",
    "questionDetail.relatedQuestions": "関連する質問",
    "questionDetail.autoTranslated": "自動翻訳",
    "questionDetail.autoTranslatedReviewed": "レビュー済みの内容を自動翻訳",

    // askAiBox
    "askAiBox.heading": "AIに質問する",

    // referencedQuestions
    "referencedQuestions.heading": "回答生成時に参考にしたQA:",

    // login
    "login.email": "メールアドレス",
    "login.password": "パスワード",
    "login.invalidCredentials": "メールアドレスまたはパスワードが正しくありません。",
    "login.loggingIn": "ログイン中...",
    "login.title": "ログイン",
    "login.studentHeading": "生徒の方",
    "login.studentHint":
        "Googleアカウントでログインすると、AIに質問できる回数が増えます。学校のGoogleアカウントで「アクセスがブロックされました」と表示される場合は、個人のGoogleアカウントをお使いください。",
    "login.withGoogle": "Googleでログイン",
    "login.adminHeading": "管理者の方",
    "login.googleFailed": "Googleログインに失敗しました。もう一度お試しください。",
    "login.accountExists":
        "このメールアドレスはパスワードで登録されています。管理者ログインをお使いください。",

    // admin (admin/questions/page.tsx only)
    "admin.status.unreviewed": "未レビュー",
    "admin.status.approved": "承認済み",
    "admin.status.rejected": "却下",
    "admin.confirmBulkDelete": "選択した質問を削除しますか？",
    "admin.confirmBulkApprove": "選択した質問を承認しますか？",
    "admin.confirmBulkReject": "選択した質問を却下しますか？",
    "admin.confirmBulkExtract": "選択した質問のConceptを抽出しますか？",
    "admin.extractLabel": "抽出",
    "admin.confirmBulkTranslate": "選択した質問の不足している言語を自動翻訳しますか？",
    "admin.translateLabel": "翻訳",
    "admin.bulkTranslatedCount": "{count}件を翻訳しました。",
    "admin.machineProvenance": "自動翻訳",
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

    // admin shared
    "adminLayout.checking": "確認中...",
    "adminLayout.adminOnly": "このページには管理者権限が必要です。",
    "common.create": "作成",
    "common.creating": "作成中...",
    "common.save": "保存",
    "common.saving": "保存中...",
    "common.register": "登録",
    "common.registering": "登録中...",
    "common.backToQuestions": "質問一覧へ戻る",
    "form.questionLabel": "質問",
    "form.answerLabel": "回答",
    "form.questionRequired": "質問を入力してください。",
    "form.answerRequired": "回答を入力してください。",

    // admin users
    "users.title": "ユーザー管理",
    "users.newTitle": "ユーザー作成",
    "users.newButton": "新規作成",
    "users.emailLabel": "メールアドレス",
    "users.emailRequired": "メールアドレスを入力してください。",
    "users.passwordLabel": "パスワード",
    "users.passwordTooShort": "8文字以上で入力してください。",
    "users.roleLabel": "権限",
    "users.roleUser": "一般ユーザー",
    "users.roleAdmin": "管理者",
    "users.created": "ユーザーを作成しました。",
    "users.createFailed": "ユーザーの作成に失敗しました。",
    "users.deleted": "ユーザーを削除しました。",
    "users.deleteFailed": "ユーザーの削除に失敗しました。",
    "users.fetchFailed": "ユーザー一覧を取得できませんでした。",
    "users.empty": "登録されているユーザーがいません。",
    "users.registeredOn": "登録日",
    "users.providerGoogle": "Google",
    "users.providerPassword": "パスワード",
    "users.confirmDelete": "ユーザーを削除しますか？",

    // admin question forms
    "questionForm.newTitle": "質問登録",
    "questionForm.registered": "登録しました。",
    "questionForm.registerFailed": "登録に失敗しました。",
    "editQuestion.title": "質問編集",
    "editQuestion.pairRequired": "質問と回答は両方入力してください。",
    "editQuestion.oneLanguageRequired":
        "少なくとも1つの言語で質問と回答を入力してください。",
    "editQuestion.updated": "更新しました。",
    "editQuestion.updateFailed": "更新に失敗しました。",
    "editQuestion.savedAndApproved": "保存して承認しました。",
    "editQuestion.actionFailed": "処理に失敗しました。",
    "editQuestion.translated": "不足している言語を翻訳しました。",
    "editQuestion.translateFailed": "翻訳に失敗しました。",
    "editQuestion.fetchFailed": "質問を取得できませんでした。",
    "editQuestion.saveAndApprove": "保存して承認",
    "editQuestion.translating": "翻訳中...",
    "editQuestion.translateMissing": "不足言語を自動翻訳",
    "provenance.original": "原文",
    "provenance.human": "人による翻訳",
    "provenance.missing": "未翻訳",

    // review history
    "reviews.title": "レビュー履歴",
    "reviews.fetchFailed": "レビュー履歴を取得できませんでした。",
    "reviews.empty": "レビュー履歴がありません。",
    "reviews.reviewerId": "レビュアーID",
    "reviews.before": "変更前",
    "reviews.after": "変更後",
    "reviews.comment": "コメント",
    "reviews.actionEditApprove": "編集して承認",

    // JSONL upload
    "upload.title": "JSONLアップロード",
    "upload.fileLabel": "JSONLファイル(複数選択可)",
    "upload.dropHint": "ファイルをドラッグ&ドロップ、またはクリックして選択",
    "upload.dropFormat": ".jsonl形式のファイル(複数選択可)",
    "upload.fileRequired": "JSONLファイルを選択してください。",
    "upload.uploadFailed": "登録に失敗しました。",
    "upload.invalidFile": "ファイルの内容に誤りがあります。",
    "upload.duplicateFile": "既存の質問と重複する内容が含まれています。",
    "upload.sourceLabel": "登録元",
    "upload.sourceAi": "AI生成",
    "upload.sourceManual": "手動",
    "upload.statusLabel": "登録時のステータス",
    "upload.resultPending": "待機中",
    "upload.resultUploading": "登録中...",
    "upload.resultSuccess": "成功",
    "upload.resultSuccessCount": "成功({count}件)",
    "upload.resultDuplicate": "重複エラー",
    "upload.resultInvalid": "内容エラー",
    "upload.resultError": "失敗",
    "upload.summary":
        "{total}ファイル中{success}ファイルが成功し、計{created}件の質問を登録しました。",

    // privacy
    "privacy.title": "プライバシーポリシー",
    "privacy.lastUpdated": "最終更新日: {date}",
    "privacy.intro":
        "Physics AI Tutor(以下「本サービス」)は、高校物理の学習を支援する質問・回答サービスです。本ページでは、本サービスが保存する情報と、その扱いを説明します。",
    "privacy.collect.heading": "保存する情報",
    "privacy.collect.account":
        "アカウント情報(Googleログイン時): メールアドレス、Googleアカウントの識別子、権限(生徒/管理者)、登録日時。",
    "privacy.collect.questions":
        "質問内容: AIに送信した質問文と生成された回答は、学習データベースの一部として保存されます。現在、質問文はアカウントと紐付けられていません。",
    "privacy.collect.usage":
        "利用記録: 利用回数制限のため、リクエストの日時をIPアドレスまたはアカウント単位で記録します。この記録は約1日で自動削除されます。",
    "privacy.collect.cookies":
        "Cookie等: ログイン状態を保持するCookie、Googleログイン処理中の一時的なCookie、表示言語の設定(ブラウザ内保存)を使用します。広告や行動追跡には使用しません。",
    "privacy.notCollect.heading": "収集しない情報",
    "privacy.notCollect.body":
        "Googleログインで取得するのはメールアドレスと識別子のみです。氏名、プロフィール画像、連絡先など、その他のGoogleアカウント情報は取得しません。アクセス解析ツールや広告は使用していません。",
    "privacy.purpose.heading": "利用目的",
    "privacy.purpose.login":
        "ログインと権限の管理(生徒・管理者の区別)のため。",
    "privacy.purpose.abuse":
        "不正利用の防止と、AI利用回数の管理のため。",
    "privacy.purpose.content":
        "質問と回答を教員がレビューし、学習データベースを改善するため。",
    "privacy.thirdParties.heading": "外部サービスへの提供",
    "privacy.thirdParties.intro":
        "本サービスは以下の外部サービスを利用します。法令に基づく場合を除き、これら以外に情報を提供しません。",
    "privacy.thirdParties.google":
        "Google: ログイン認証のため。認証はGoogleのプライバシーポリシーに従います。",
    "privacy.thirdParties.llm":
        "DeepSeek・OpenAI: 回答の生成と検索のため、質問文を送信します。アカウント情報は送信しません。",
    "privacy.thirdParties.hosting":
        "Vercel・Render・Supabase: サービスの運用とデータの保管のため。",
    "privacy.retention.heading": "保存期間",
    "privacy.retention.body":
        "アカウント情報は、削除の申し出があるまで保存します。利用記録は約1日で削除されます。質問と回答は教育コンテンツとして保存され、アカウントとは紐付けられません。",
    "privacy.deletion.heading": "アカウントの削除",
    "privacy.deletion.body":
        "ログイン中は、アカウントページからいつでも自分でアカウントを削除できます。ログインできない場合は、下記の連絡先にご依頼ください。",
    "privacy.deletion.linkLabel": "アカウントページへ",
    "privacy.contact.heading": "お問い合わせ",
    "privacy.contact.body":
        "本ポリシーに関する質問や削除の依頼は、次の窓口までお願いします:",
    "privacy.contact.linkLabel": "お問い合わせ窓口",
    "privacy.changes.heading": "本ポリシーの変更",
    "privacy.changes.body":
        "保存する情報や利用目的が変わる場合は、本ページを更新します。重要な変更はログインページでお知らせします。",


    // account
    "account.title": "アカウント",
    "account.emailLabel": "メールアドレス",
    "account.providerLabel": "ログイン方法",
    "account.registeredLabel": "登録日",
    "account.fetchFailed": "アカウント情報を取得できませんでした。",
    "account.deleteHeading": "アカウントの削除",
    "account.deleteDescription":
        "アカウント情報(メールアドレスなど)を削除します。これまでに保存された質問と回答は、アカウントと紐付いていないため残ります。この操作は取り消せません。",
    "account.deleteButton": "アカウントを削除",
    "account.confirmDelete": "本当にアカウントを削除しますか？",
    "account.deleted": "アカウントを削除しました。",
    "account.deleteFailed": "アカウントの削除に失敗しました。",
    "account.adminNote":
        "管理者アカウントはここからは削除できません。ユーザー管理画面から別の管理者が削除してください。",

    // footer
    "footer.privacy": "プライバシーポリシー",

    // error / not found / markdown
    "errorPage.title": "エラーが発生しました",
    "errorPage.description": "しばらくしてから再度お試しください。",
    "errorPage.retry": "再試行",
    "notFound.title": "ページが見つかりません",
    "notFound.description": "お探しのページは存在しないか、削除された可能性があります。",
    "notFound.backHome": "トップへ戻る",
    "markdown.hasDiagram": "図を含む",
    "markdown.diagramFailed": "図を表示できませんでした。",
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
    "header.login": "Login",
    "header.account": "Account",
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
    "questionSearch.answerUnreviewed":
        "This AI answer has not been checked by a teacher yet.",
    "questionSearch.cachedNotice":
        "Showing a previous answer to the same question.",

    // questionDetail
    "questionDetail.alreadyAnswered":
        "An answer to this question has already been generated",
    "questionDetail.unreviewedBadge": "Not reviewed by admin",
    "questionDetail.relatedQuestions": "Related Questions",
    "questionDetail.autoTranslated": "Auto-translated",
    "questionDetail.autoTranslatedReviewed":
        "Auto-translated from reviewed content",

    // askAiBox
    "askAiBox.heading": "Ask AI",

    // referencedQuestions
    "referencedQuestions.heading": "Referenced Q&A used to generate this answer:",

    // login
    "login.email": "Email",
    "login.password": "Password",
    "login.invalidCredentials": "Invalid email or password.",
    "login.loggingIn": "Logging in...",
    "login.title": "Login",
    "login.studentHeading": "Students",
    "login.studentHint":
        "Signing in with Google raises your AI question allowance. If your school Google account shows \"Access blocked\", use a personal Google account instead.",
    "login.withGoogle": "Sign in with Google",
    "login.adminHeading": "Administrators",
    "login.googleFailed": "Google sign-in failed. Please try again.",
    "login.accountExists":
        "This email is registered with a password. Please use the admin login.",

    // admin (admin/questions/page.tsx only)
    "admin.status.unreviewed": "Unreviewed",
    "admin.status.approved": "Approved",
    "admin.status.rejected": "Rejected",
    "admin.confirmBulkDelete": "Delete the selected questions?",
    "admin.confirmBulkApprove": "Approve the selected questions?",
    "admin.confirmBulkReject": "Reject the selected questions?",
    "admin.confirmBulkExtract": "Extract concepts for the selected questions?",
    "admin.extractLabel": "Extract",
    "admin.confirmBulkTranslate":
        "Machine translate the missing languages of the selected questions?",
    "admin.translateLabel": "Translate",
    "admin.bulkTranslatedCount": "Translated {count} questions.",
    "admin.machineProvenance": "Auto-translated",
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

    // admin shared
    "adminLayout.checking": "Checking...",
    "adminLayout.adminOnly": "This page requires administrator privileges.",
    "common.create": "Create",
    "common.creating": "Creating...",
    "common.save": "Save",
    "common.saving": "Saving...",
    "common.register": "Submit",
    "common.registering": "Submitting...",
    "common.backToQuestions": "Back to questions",
    "form.questionLabel": "Question",
    "form.answerLabel": "Answer",
    "form.questionRequired": "Please enter a question.",
    "form.answerRequired": "Please enter an answer.",

    // admin users
    "users.title": "Manage Users",
    "users.newTitle": "Create User",
    "users.newButton": "New user",
    "users.emailLabel": "Email",
    "users.emailRequired": "Please enter an email address.",
    "users.passwordLabel": "Password",
    "users.passwordTooShort": "Enter at least 8 characters.",
    "users.roleLabel": "Role",
    "users.roleUser": "User",
    "users.roleAdmin": "Administrator",
    "users.created": "User created.",
    "users.createFailed": "Failed to create the user.",
    "users.deleted": "User deleted.",
    "users.deleteFailed": "Failed to delete the user.",
    "users.fetchFailed": "Failed to load users.",
    "users.empty": "No users found.",
    "users.registeredOn": "Registered",
    "users.providerGoogle": "Google",
    "users.providerPassword": "Password",
    "users.confirmDelete": "Delete this user?",

    // admin question forms
    "questionForm.newTitle": "Register Question",
    "questionForm.registered": "Registered.",
    "questionForm.registerFailed": "Failed to register.",
    "editQuestion.title": "Edit Question",
    "editQuestion.pairRequired": "Enter both the question and the answer.",
    "editQuestion.oneLanguageRequired":
        "Enter a question and answer in at least one language.",
    "editQuestion.updated": "Updated.",
    "editQuestion.updateFailed": "Failed to update.",
    "editQuestion.savedAndApproved": "Saved and approved.",
    "editQuestion.actionFailed": "The operation failed.",
    "editQuestion.translated": "Translated the missing language.",
    "editQuestion.translateFailed": "Translation failed.",
    "editQuestion.fetchFailed": "Failed to load the question.",
    "editQuestion.saveAndApprove": "Save & approve",
    "editQuestion.translating": "Translating...",
    "editQuestion.translateMissing": "Translate missing language",
    "provenance.original": "Original",
    "provenance.human": "Human translation",
    "provenance.missing": "Not translated",

    // review history
    "reviews.title": "Review History",
    "reviews.fetchFailed": "Failed to load the review history.",
    "reviews.empty": "No review history.",
    "reviews.reviewerId": "Reviewer ID",
    "reviews.before": "Before",
    "reviews.after": "After",
    "reviews.comment": "Comment",
    "reviews.actionEditApprove": "Edit & approve",

    // JSONL upload
    "upload.title": "JSONL Upload",
    "upload.fileLabel": "JSONL files (multiple allowed)",
    "upload.dropHint": "Drag & drop files here, or click to select",
    "upload.dropFormat": ".jsonl files (multiple allowed)",
    "upload.fileRequired": "Please select a JSONL file.",
    "upload.uploadFailed": "Upload failed.",
    "upload.invalidFile": "The file contents are invalid.",
    "upload.duplicateFile": "Contains questions that duplicate existing ones.",
    "upload.sourceLabel": "Source",
    "upload.sourceAi": "AI generated",
    "upload.sourceManual": "Manual",
    "upload.statusLabel": "Status on import",
    "upload.resultPending": "Waiting",
    "upload.resultUploading": "Uploading...",
    "upload.resultSuccess": "Success",
    "upload.resultSuccessCount": "Success ({count})",
    "upload.resultDuplicate": "Duplicate error",
    "upload.resultInvalid": "Content error",
    "upload.resultError": "Failed",
    "upload.summary":
        "{success} of {total} files succeeded; {created} questions were registered.",


    // privacy
    "privacy.title": "Privacy Policy",
    "privacy.lastUpdated": "Last updated: {date}",
    "privacy.intro":
        "Physics AI Tutor (\"this service\") is a Q&A service that supports learning high school physics. This page explains what information the service stores and how it is handled.",
    "privacy.collect.heading": "Information we store",
    "privacy.collect.account":
        "Account information (when you sign in with Google): your email address, your Google account identifier, your role (student/administrator), and the registration date.",
    "privacy.collect.questions":
        "Questions: the questions you send to the AI and the generated answers are stored as part of the learning database. Questions are currently not linked to your account.",
    "privacy.collect.usage":
        "Usage records: to enforce ask limits, we record request timestamps per IP address or per account. These records are deleted automatically after about one day.",
    "privacy.collect.cookies":
        "Cookies and similar: a cookie that keeps you signed in, a temporary cookie during Google sign-in, and your language preference (stored in your browser). None are used for advertising or tracking.",
    "privacy.notCollect.heading": "Information we do not collect",
    "privacy.notCollect.body":
        "Google sign-in provides only your email address and account identifier. We do not receive your name, profile picture, contacts, or any other Google account data. The site uses no analytics tools and no advertising.",
    "privacy.purpose.heading": "Why we store it",
    "privacy.purpose.login":
        "To sign you in and manage roles (student vs. administrator).",
    "privacy.purpose.abuse":
        "To prevent abuse and manage the AI ask limits.",
    "privacy.purpose.content":
        "So teachers can review questions and answers and improve the learning database.",
    "privacy.thirdParties.heading": "Third-party services",
    "privacy.thirdParties.intro":
        "The service relies on the following providers. Beyond these, information is not shared unless required by law.",
    "privacy.thirdParties.google":
        "Google: for sign-in. Authentication is governed by Google's privacy policy.",
    "privacy.thirdParties.llm":
        "DeepSeek and OpenAI: question text is sent to generate and search answers. No account information is sent.",
    "privacy.thirdParties.hosting":
        "Vercel, Render, and Supabase: to run the service and store its data.",
    "privacy.retention.heading": "Retention",
    "privacy.retention.body":
        "Account information is kept until you ask us to delete it. Usage records are deleted after about one day. Questions and answers are kept as educational content and are not linked to accounts.",
    "privacy.deletion.heading": "Deleting your account",
    "privacy.deletion.body":
        "While signed in, you can delete your account yourself at any time from the account page. If you can no longer sign in, send a request to the contact below.",
    "privacy.deletion.linkLabel": "Go to the account page",
    "privacy.contact.heading": "Contact",
    "privacy.contact.body":
        "For questions about this policy or deletion requests, please use:",
    "privacy.contact.linkLabel": "Contact page",
    "privacy.changes.heading": "Changes to this policy",
    "privacy.changes.body":
        "If what we store or why changes, this page will be updated. Important changes will be announced on the login page.",


    // account
    "account.title": "Account",
    "account.emailLabel": "Email",
    "account.providerLabel": "Sign-in method",
    "account.registeredLabel": "Registered",
    "account.fetchFailed": "Failed to load your account.",
    "account.deleteHeading": "Delete account",
    "account.deleteDescription":
        "This removes your account information (such as your email address). Questions and answers already saved remain, because they are not linked to your account. This cannot be undone.",
    "account.deleteButton": "Delete my account",
    "account.confirmDelete": "Really delete your account?",
    "account.deleted": "Your account has been deleted.",
    "account.deleteFailed": "Failed to delete your account.",
    "account.adminNote":
        "Administrator accounts cannot be deleted here. Ask another administrator to remove it from the user management page.",

    // footer
    "footer.privacy": "Privacy Policy",

    // error / not found / markdown
    "errorPage.title": "Something went wrong",
    "errorPage.description": "Please try again in a moment.",
    "errorPage.retry": "Retry",
    "notFound.title": "Page not found",
    "notFound.description":
        "The page you are looking for does not exist or may have been removed.",
    "notFound.backHome": "Back to home",
    "markdown.hasDiagram": "Contains a diagram",
    "markdown.diagramFailed": "Failed to display the diagram.",
};

export const translations = { ja, en };
export type TranslationKey = keyof typeof ja;
