// Login, account and privacy pages ([64]).

export const ja = {
    "login.email": "メールアドレス",
    "login.password": "パスワード",
    "login.invalidCredentials":
        "メールアドレスまたはパスワードが正しくありません。",
    "login.loggingIn": "ログイン中...",
    "login.title": "ログイン",
    "login.studentHeading": "生徒の方",
    "login.studentHint":
        "Googleアカウントでログインすると、AIに質問できる回数が増えます。学校のGoogleアカウントで「アクセスがブロックされました」と表示される場合は、個人のGoogleアカウントをお使いください。",
    "login.withGoogle": "Googleでログイン",
    "login.adminHeading": "管理者の方",
    "login.googleFailed":
        "Googleログインに失敗しました。もう一度お試しください。",
    "login.accountExists":
        "このメールアドレスはパスワードで登録されています。管理者ログインをお使いください。",
    "privacy.title": "プライバシーポリシー",
    "privacy.lastUpdated": "最終更新日: {date}",
    "privacy.intro":
        "Physics AI Tutor(以下「本サービス」)は、高校物理の学習を支援する質問・回答サービスです。本ページでは、本サービスが保存する情報と、その扱いを説明します。",
    "privacy.collect.heading": "保存する情報",
    "privacy.collect.account":
        "アカウント情報(Googleログイン時): メールアドレス、Googleアカウントの識別子、権限(生徒/管理者)、登録日時。",
    "privacy.collect.questions":
        "質問内容: AIに送信した質問文と生成された回答は、学習データベースの一部として保存されます。ログインして質問した場合は、「自分の質問」ページを表示するために、どの質問をいつ尋ねたかがアカウントに紐付けて記録されます。",
    "privacy.collect.usage":
        "利用記録: 利用回数制限のため、リクエストの日時をIPアドレスまたはアカウント単位で記録します。この記録は約1日で自動削除されます。",
    "privacy.collect.cookies":
        "Cookie等: ログイン状態を保持するCookie、Googleログイン処理中の一時的なCookie、表示言語の設定(ブラウザ内保存)を使用します。広告や行動追跡には使用しません。",
    "privacy.notCollect.heading": "収集しない情報",
    "privacy.notCollect.body":
        "Googleログインで取得するのはメールアドレスと識別子のみです。氏名、プロフィール画像、連絡先など、その他のGoogleアカウント情報は取得しません。アクセス解析ツールや広告は使用していません。",
    "privacy.purpose.heading": "利用目的",
    "privacy.purpose.login": "ログインと権限の管理(生徒・管理者の区別)のため。",
    "privacy.purpose.abuse": "不正利用の防止と、AI利用回数の管理のため。",
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
        "アカウント情報は、削除の申し出があるまで保存します。利用記録は約1日で削除されます。質問と回答は教育コンテンツとして保存されます。アカウントを削除すると、質問履歴とアカウントの紐付けは解除されます。",
    "privacy.retention.devNotice":
        "本サービスは開発中です。データは安全に管理するよう努めていますが、開発上の都合(データベース構成の変更やサービスの終了など)により、保存されている情報を予告なく削除する場合があります。",
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
    "account.title": "アカウント",
    "account.emailLabel": "メールアドレス",
    "account.providerLabel": "ログイン方法",
    "account.registeredLabel": "登録日",
    "account.fetchFailed": "アカウント情報を取得できませんでした。",
    "account.deleteHeading": "アカウントの削除",
    "account.deleteDescription":
        "アカウント情報(メールアドレスなど)を削除し、質問履歴との紐付けも解除します。保存された質問と回答自体は学習データベースに残ります。この操作は取り消せません。",
    "account.deleteButton": "アカウントを削除",
    "account.confirmDelete": "本当にアカウントを削除しますか？",
    "account.deleted": "アカウントを削除しました。",
    "account.deleteFailed": "アカウントの削除に失敗しました。",
    "account.adminNote":
        "管理者アカウントはここからは削除できません。ユーザー管理画面から別の管理者が削除してください。",
} as const;

export const en: Record<keyof typeof ja, string> = {
    "login.email": "Email",
    "login.password": "Password",
    "login.invalidCredentials": "Invalid email or password.",
    "login.loggingIn": "Logging in...",
    "login.title": "Login",
    "login.studentHeading": "Students",
    "login.studentHint":
        'Signing in with Google raises your AI question allowance. If your school Google account shows "Access blocked", use a personal Google account instead.',
    "login.withGoogle": "Sign in with Google",
    "login.adminHeading": "Administrators",
    "login.googleFailed": "Google sign-in failed. Please try again.",
    "login.accountExists":
        "This email is registered with a password. Please use the admin login.",
    "privacy.title": "Privacy Policy",
    "privacy.lastUpdated": "Last updated: {date}",
    "privacy.intro":
        'Physics AI Tutor ("this service") is a Q&A service that supports learning high school physics. This page explains what information the service stores and how it is handled.',
    "privacy.collect.heading": "Information we store",
    "privacy.collect.account":
        "Account information (when you sign in with Google): your email address, your Google account identifier, your role (student/administrator), and the registration date.",
    "privacy.collect.questions":
        'Questions: the questions you send to the AI and the generated answers are stored as part of the learning database. When you ask while signed in, which question you asked and when is linked to your account so the "My questions" page can show your history.',
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
    "privacy.purpose.abuse": "To prevent abuse and manage the AI ask limits.",
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
        "Account information is kept until you ask us to delete it. Usage records are deleted after about one day. Questions and answers are kept as educational content. Deleting your account removes the link between your account and your question history.",
    "privacy.retention.devNotice":
        "This service is still under development. We take reasonable care to keep data safe, but stored information may be deleted without notice for development reasons, such as database schema changes or discontinuing the service.",
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
    "account.title": "Account",
    "account.emailLabel": "Email",
    "account.providerLabel": "Sign-in method",
    "account.registeredLabel": "Registered",
    "account.fetchFailed": "Failed to load your account.",
    "account.deleteHeading": "Delete account",
    "account.deleteDescription":
        "This removes your account information (such as your email address) and unlinks your question history. The saved questions and answers themselves remain in the learning database. This cannot be undone.",
    "account.deleteButton": "Delete my account",
    "account.confirmDelete": "Really delete your account?",
    "account.deleted": "Your account has been deleted.",
    "account.deleteFailed": "Failed to delete your account.",
    "account.adminNote":
        "Administrator accounts cannot be deleted here. Ask another administrator to remove it from the user management page.",
};
