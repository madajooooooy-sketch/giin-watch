# 国会議員活動ウォッチ v0.8

## 新機能
衆参の公式議員一覧ページから候補名簿を取得する試験的スクリプト `tools/fetch_official.py` を追加しました。GitHub Actionsの週次実行設定付きです。取得した名簿は `reports/candidates.json` に出力され、**公開中の `data/members.json` は変更しません**。公式ページの構造変更、文字コード、行見出しの違いにより取得件数が不正確になる場合があります。

## Windowsでの実行
1. Python 3.12以降をインストール。
2. ZIPを展開してフォルダ内でターミナルを開く。
3. `python -m pip install -r requirements.txt`
4. `python tools/fetch_official.py`
5. `reports/fetch-report.json` のエラー・件数を確認し、`reports/candidates.json` を公式ページと照合。
6. 正確性を人が確認した場合に限り、`data/members.json` をバックアップして差し替え。

## GitHubでの利用
リポジトリにアップロードすると、Actionsから手動実行でき、毎週月曜日に候補を取得します。Actionsの実行結果のArtifactsから候補をダウンロードしてください。自動公開はしません。

## 注意
取得処理は実験的なものです。公式サイトの利用条件とアクセス頻度を守ってください。衆議院のページは50音別の構造があり、参議院は会期別の構造があるため、取得結果は完全とは限りません。サイト同梱名簿は前バージョンの5件で、全現職名簿ではありません。政党と会派は異なる概念で、公式表記の会派を party に暫定格納しています。公開前にデータモデルを分離してください。
