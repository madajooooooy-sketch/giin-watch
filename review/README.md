# 名簿の確認室

既存トップページ・data/members.jsonから独立した、公式名簿の候補確認画面です。

- 名前・読み・選挙区・会派の検索（空白、全半角、ひらがな・カタカナの違いを吸収）
- 議院・会派の絞り込み、読み順・選挙区順、24件ごとのページ切り替え
- 詳細と公式出典、検索結果のCSV出力（Excel用BOM・数式対策付き）
- キーボード操作、スマートフォン表示、読込失敗時の再試行

`parliamentary_group` は議院公式表の会派、`party` は党の公式出典で照合した所属政党です。出典がない所属はnull（未確認）を維持します。政党確認日と名簿取得日は別です。政党の照合は、氏名・議院の完全一致を優先し、表記違いは読み・議院が一意に一致する場合だけ採用します。同じ読みの別人は割り当てません。根拠はparty-evidence.json、取得元と照合件数はparty-check-report.jsonに記録します。

2026年10月23日現在、7党595人（民主改革の会18人を含む）を出典確認、116人は未確認。立憲民主党・公明党等の一覧取得ができなかったものや未登録の党・無所属は推測で埋めていません。会派「中道」を一律に民主改革の会へ変える処理はありません。

## 更新方法

リポジトリのルートで実行します。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tools/tests -v
python tools/fetch_official.py
python tools/validate_candidates.py reports/candidates.json
python tools/fetch_parties.py --candidates reports/candidates.json
# reports/party-change-report.jsonを確認後、確認済みの根拠だけ採用
# review/party-evidence.jsonを更新してから再生成
python tools/build_review.py reports/candidates.json
```

生成結果はreview/members-review.jsonとreview/quality-report.jsonだけです。確認後にコミットしてください。自動で公開データを差し替える処理はありません。

## 継続確認

既存の週次Actionsで、登録した各党の公式出典を再取得し、所属の変更候補・名簿の増減・再確認できなかった所属をreports/party-change-report.jsonへ出力します。取得失敗や一覧からの欠落を離党と断定しません。自動で公開画面を書き換えません。

新党の自動発見・無審査の所属変更には対応しません。新しい政党はtools/fetch_parties.pyのSOURCESに公式出典と取得処理を追加して対応します。今回、民主改革の会の公式note「議員紹介」を登録しました。公式ページの構造変更・改称も定期的な点検が必要です。

ローカル表示は `python -m http.server 8765` を起動し、http://localhost:8765/review/ を開きます。HTMLの直接ダブルクリックではJSON読込が制限される場合があります。
