# Todo Progress App

Streamlit で作ったやることリストです。

## 機能
- タスク追加 / 編集 / 削除
- 完了チェック
- 達成率表示
- 優先度
- 期限
- 絞り込み
- 並び替え
- ブラウザのローカル保存

## 保存仕様
この版は **ブラウザの localStorage** に保存します。
そのため、**同じブラウザ・同じ端末** であれば、ページを閉じても内容が残ります。

注意:
- 別の端末や別のブラウザには同期されません
- ブラウザの保存データを消すとタスクも消えます
- 完全なクラウド同期が必要なら Supabase / Firebase / SQLite + 外部ストレージ などが必要です

## ローカル実行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud
- Repository: このリポジトリ
- Branch: `main`
- File path: `app.py`

## GitHub にアップロード
ZIP を展開して、中のファイルをそのまま GitHub にアップロードしてください。
