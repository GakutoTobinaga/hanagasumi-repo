# 結果画像の索引

※ 元画像は幅1600pxに縮小。生成元のスクリプトは `src/` を参照。画像のうち、Workbenchの照明で暗く見えるものは、色の見え方が実際の設定とは違う（陰影なしの `*_colors_*` で設定色を確認）。

## Cloth検証①: 742頂点（輪郭=shield）、自己衝突OFF。列=成長量(0/0.12/0.25/0.4)、行=曲げ剛性

- `cloth_test_low.png`
- `cloth_test_oblique.png`

## Cloth検証②: 3420頂点。縁の縮れが細かく枝分かれする（メッシュ密度の効果）

- `cloth_fine_low.png`
- `cloth_fine_oblique.png`

## Cloth検証③: 自己衝突ON、成長0.25/0.4/0.6

- `cloth_selfcol_low.png`
- `cloth_selfcol_oblique.png`

## Cloth検証④: 初期形状に縁の反り返り(curl)を足した版。B=curlのみ、C=cup+curl。先端に『つまみ』状の折れ返りが出た

- `cloth_curl_B_low.png`
- `cloth_curl_B_oblique.png`
- `cloth_curl_C_low.png`
- `cloth_curl_C_oblique.png`

## Cloth検証⑤: 扇形の輪郭＋curl0.10＋先端curl弱め（F10）

- `cloth_F10_low.png`
- `cloth_F10_oblique.png`

## 同: curl0.18（皿のように垂れる）

- `cloth_F18_oblique.png`

## 同: 旧輪郭(shield)で先端curl弱め

- `cloth_S10_oblique.png`

## Cloth検証⑥: 成長ベースの放射状ひだ（P=ひだのみ、PA=+非対称、PAT=+異方的湾曲）。ひだはくしゃくしゃになった（等方成長が原因という仮説）

- `cloth_pleat_PAT_low.png`
- `cloth_pleat_PAT_oblique.png`
- `cloth_pleat_PA_oblique.png`
- `cloth_pleat_P_oblique.png`

## Cloth検証⑦: 初期形状に解析式の放射状ひだ（amp0=なし、amp006=0.06）。ひだが明確に出る（貝殻状）

- `cloth_pleatinit_amp006_oblique.png`
- `cloth_pleatinit_amp0_oblique.png`

## Cloth検証⑧: ひだの位置・振幅のムラと二次ひだ(枝分かれの近似)。f15=15本設定、f30=30本設定

- `cloth_irreg_f15_oblique.png`
- `cloth_irreg_f30_low.png`
- `cloth_irreg_f30_oblique.png`

## Cloth検証⑨: 縁のcurlを片側に偏らせた版（右側に大きな折り返し）

- `cloth_curlasym_low.png`
- `cloth_curlasym_oblique.png`

## 同: 一様なcurl（比較用）

- `cloth_curluniform_oblique.png`

## Cloth検証⑩: h=0.007(約1.7万頂点)+自己衝突ON。シミュレーションが破綻（成長ゼロの列まで潰れた）。比較に使えない

- `cloth_h007_low.png`
- `cloth_h007_oblique.png`

## 同: h=0.014（比較用、正常）

- `cloth_h014_oblique.png`

## Meshy見本1の測定図（粗さ・折れ目の本数・輪郭からの距離）

- `meshy_petal_analysis.png`

## 同: 見本1

- `meshy_petal1_analysis.png`

## 同: 見本2（wavy）

- `meshy_petal2_analysis.png`

## Meshy見本3〜6の測定図（p3=t3 … p6=t6）。※t4,t6は付け根の自動検出が誤っていた時点の図

- `meshy_p3_bottom_left.png`
- `meshy_p4_bottom_right.png`
- `meshy_p5_fan.png`
- `meshy_p6_top_right.png`

## 付け根の確認画像。赤=自動検出した付け根、青=反対側。t1,t2,t3,t5は赤が正しい。t4,t6は赤が誤り（正しい付け根は正面の右下の尖った端、ユーザーが確認）

- `axes_t1.png`
- `axes_t2.png`
- `axes_t4.png`
- `axes_t6.png`

## 型の連続変形（original / width0.8 / width1.2 / bend+0.3 / trough0.3 / combo）。折れ目が保たれる

- `deform_t3_3q.png`
- `deform_t3_front.png`
- `deform_t5_3q.png`
- `deform_t5_front.png`

## 花全体の試作（6種類の花F1〜F6）。_34=斜め上(Workbench照明で暗く見える)、_top=真上、_colors_flat=陰影なし（設定した色とグラデーション）

- `flower_proto_34.png`
- `flower_proto_colors_flat.png`
- `flower_proto_top.png`

## 交配試験①（親F2×F3、左列が親、右が子6つ）。半径が親の範囲外になる問題が出た版

- `breeding_34.png`
- `breeding_colors_top.png`

## 交配試験②: 半径を独立遺伝子にした版（高さが親の範囲外になった）

- `breeding2_34.png`
- `breeding2_colors_top.png`

## 交配試験③: 半径と高さを独立遺伝子にした版

- `breeding3_34.png`
- `breeding3_colors_top.png`

## 世代試験①: 12世代目の8個体。選別なしのランダム交配で、全部が似た紫ピンクに収束した（問題発見）

- `generations_g12_34.png`
- `generations_g12_colors.png`

## 世代試験②: 層の修正＋K=0.45。多様性が戻った

- `generations2_g12_34.png`
- `generations2_g12_colors.png`

## 世代試験③: 開き角を自動決定＋遺伝子ごとの調整。歪みなし

- `generations3_g12_34.png`
- `generations3_g12_colors.png`
