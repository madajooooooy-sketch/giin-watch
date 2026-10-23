# 名簿の確認室

既存トップページ・data/members.jsonから独立した、公式名簿の候補確認画面です。

- 名前・読み・選挙区・会派の検索（空白、全半角、ひらがな・カタカナの違いを吸収）
- 議院・会派の絞り込み、読み順・選挙区順、24件ごとのページ切り替え
- 詳細と公式出典、検索結果のCSV出力（Excel用BOM・数式対策付き）
- キーボード操作、スマートフォン表示、読込失敗時の再試行

`party` はnull、`parliamentary_group` は公式表の会派です。政党は未確認のまま保存します。取得日と個別確認日を混同しません。公式リンクで氏名などを個別に確かめるための候補であり、人による確認済み名簿ではありません。

## 更新方法

リポジトリのルートで実行します。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tools/tests -v
python tools/fetch_official.py
python tools/validate_candidates.py reports/candidates.json
python tools/build_review.py reports/candidates.json
```

生成結果はreview/members-review.jsonとreview/quality-report.jsonだけです。確認後にコミットしてください。自動で公開データを差し替える処理はありません。

ローカル表示は `python -m http.server 8765` を起動し、http://localhost:8765/review/ を開きます。HTMLの直接ダブルクリックではJSON読込が制限される場合があります。
