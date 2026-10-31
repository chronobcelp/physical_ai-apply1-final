# Physical AI 最終課題：Q-learningで障害物回避を比較する

**最も簡単な提出用パッケージ**です。Docker、ROS 2、Gazebo、GPUを必要としません。Google ColabのCPUで実行できます。

この作品は**離散的な2D格子の簡易ロボットシミュレーション**であり、実機・物理エンジンでの制御ではありません。

## 何を比較する？

1. 元の障害物12個の環境でQ-learningの学習・評価を行う。
2. **`OBSTACLES.add((3, 6))`** と同じ操作で、元の経路外に障害物を追加する。**元の学習済みAIは保持して**再学習前後を比較する。
3. 追加実験として、元の経路上 **`(6, 2)`** に障害物を置き、再学習前後を比較する。
4. 学習済みAIとランダム制御を比べ、評価表、動画、PDFを作る。

**注意:** `(3, 6)` は元の学習済みAIの経路上にありません。改善が見られなくても正しい実験結果です。`(6, 2)` による比較は、再学習の意味を明確に示す追加実験です。

## 手順A：Colabで最も簡単に動かす

1. [Google Colab](https://colab.research.google.com/) を開く。
2. 「ファイル → ノートブックをアップロード」から `PhysicalAI_比較実験_Colab.ipynb` を選ぶ。
3. 上部メニューの「ランタイム → すべてのセルを実行」を選ぶ。
4. `results/comparison_demo.mp4`（112秒）および`results/comparison_results.csv`を確認する。
5. 自動生成したPDFは、アカウント名・GitHub・YouTube URLを追加して再出力するか、同梱の`レポート文章_編集用.md`を使って編集する。
6. Notebookの最後のセルにあるダウンロード処理で提出素材を保存する。

## 手順B：ローカルのPythonで動かす

```bash
python -m pip install -r requirements.txt
python run_experiment.py
python make_report.py
```

`ffmpeg` も別途必要です。Colabでは通常インストールされています。ない場合はColab上で `!apt-get -qq install ffmpeg` を実行します。

## Notebook・ファイルの役割

| ファイル | 内容 | 提出先 |
|---|---|---|
| `PhysicalAI_比較実験_Colab.ipynb` | Colabで動く全コード | GitHub（Public） |
| `run_experiment.py` | 同じ実験をPythonで再実行 | GitHub（Public） |
| `make_report.py` | 実測値からPDFを自動生成 | GitHub（Public、任意） |
| `requirements.txt` | Pythonライブラリ | GitHub（Public） |
| `results/comparison_demo.mp4` | 112秒の実行動画 | YouTube |
| `説明資料_...pdf` | 実験結果を記載した3ページのレポート | omnicampus |
| `results/comparison_results.csv` | 比較結果一覧 | GitHub（任意） |

## 結果の読み方

デフォルト設定・乱数シード2026では次の出力を確認しました。

| 条件 | 固定スタートからの到達 | 代表的なステップ数 |
|---|---:|---:|
| 元の障害物・学習済みAI | 成功 | 14 |
| `(3, 6)`追加・元のAI | 成功 | 14 |
| `(3, 6)`追加・再学習AI | 成功 | 14 |
| `(6, 2)`追加・元のAI | 失敗 | 40（打ち切り） |
| `(6, 2)`追加・再学習AI | 成功 | 14 |

評価は**スタートとゴールが固定で、AIは決定論的**です。100回の成功率は100種類の未知環境で成功した意味ではありません。
