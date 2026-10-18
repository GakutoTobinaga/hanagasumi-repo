# 花霞（hanagasumi）— 交配ゲーム用の花の生成と遺伝子設計

交配ゲーム（PC専用）の花「花霞」の、**型（Meshyで生成した花びらモデル）＋連続変形＋花全体の遺伝子**による生成と、交配ルールの検証コード・結果・仕様書。

**新しいAI・開発者は、まず [`docs/HANDOFF.md`](docs/HANDOFF.md) を読んでください。**

## 現在の状態（2026-10-18）
- 花びらの型6種、連続変形、花の組み立て、交配ルール、50世代の集団試験まで、検証済み（選別なしのランダム交配）。
- **未実施**: 選別あり、質感の描画、花びらの突き抜けの測定、雌しべ・雄しべ。詳細は `docs/HANDOFF.md` 9章。

## 構成
| パス | 内容 |
|---|---|
| `docs/HANDOFF.md` | **引き継ぎ書**（目的、決定と根拠、環境、落とし穴、ユーザーの作業スタイル、次の一手） |
| `docs/FINDINGS.md` | 測定・試験の結果のまとめ |
| `docs/TIMELINE.md` | 経緯の要約 |
| `spec/hanagasumi_gene_spec.json` | 遺伝子仕様書（正本、v0.3.2-draft） |
| `src/` | コード（`cloth/`, `analysis/`, `flower/`, `obsolete/`） |
| `results/` | 結果画像（`images/INDEX.md`に索引）と統計（JSON） |
| `assets/` | 見本のGLB6枚（約156MB、含まれる。`assets/README.md`参照） |
| `scripts/` | 環境構築、GLBの読み込み |

## クイックスタート
```
bash scripts/setup_env.sh        # Python 3.11 + bpy 4.5.0（/tmp/bpyenv）
bash scripts/load_all_glb.sh
/tmp/bpyenv/bin/python src/flower/hanagasumi_longrun_test.py -- /tmp/meshy/long
```
詳しくは `docs/HANDOFF.md` 6章。

## 注意
- 見本のGLB6枚は含まれます（ユーザーの判断。公開リポジトリ）。見本の**写真**は、含まれません。Meshy生成物の利用は、ユーザーがMeshyに確認済みです（回答の原文は、リポジトリにありません）。条件は `NOTICE.md`。
- ライセンスは、未設定です（`NOTICE.md`）。
