# 3D preview model pipeline

`3d-preview` は、Blender の編集元データ、リポジトリ内の設計データから部品を再生成するスクリプト、検証用スクリプト、Web 向け GLB の書き出し処理をまとめたディレクトリです。

編集の中心は [`Surround1x0-AKDK.blend`](./Surround1x0-AKDK.blend) です。自動生成された部品を手作業で直すのではなく、原則として対応する入力データまたは `scripts/` 内の生成スクリプトを修正して再生成します。

## 全体の関係

```text
pcb/*.json ──────────────> build_pcb_from_repository.py ──> PCB
                                  │
                                  ├─> build_choc_hotswap_sockets.py
                                  ├─> build_controller_sensor_modules.py
                                  └─> setup_assembly_exploded_view.py

keycaps/ ────────────────> 利用者がカスタムできる3Dプリント用成果物

.blend 内のキーキャップ ─> build_choc_v2_switches.py ─────> Switches

生成済みの各部品 ─────────> verify_*.py / render_*.py ───────> .tmp/ の検証資料

更新済み .blend ─────────> setup_assembly_exploded_view.py ─> 分解レイヤー
        └────────────────> export_web_glb.py ───────────────> Black / White / Web GLB
```

基本の更新順は次のとおりです。

1. 変更対象に対応する生成スクリプトだけを実行する。PCB、ソケット、コントローラー／センサーをまとめて更新するときは `build_pcb_from_repository.py` を使う。
2. 対応する `verify_*.py` を実行する。
3. 個別の生成スクリプトを実行した場合や親子関係を変更した場合は、`setup_assembly_exploded_view.py` を再実行する。
4. Web用モデルを更新するときは、最後に `export_web_glb.py` で GLB を書き出す。

これは全工程を毎回実行するための固定ワークフローではありません。変更した部品に関係する処理だけを選んで使用します。

## 主要な生成・更新スクリプト

| スクリプト | 主な入力 | `.blend` への変更 | 保存と依存関係 |
| --- | --- | --- | --- |
| [`build_choc_v2_switches.py`](./scripts/build_choc_v2_switches.py) | `.blend` 内の既存スイッチ位置とキーキャップの `module_id` / `profile` | Kailh Choc V2 の各部品を再生成 | 単体では保存も分解レイヤー再構築もしない。実行後に保存し、続けて分解ビューを更新する |
| [`build_pcb_from_repository.py`](./scripts/build_pcb_from_repository.py) | `../pcb/Surround1x0-AKDK-{left,right}-pcb.json` | 左右 PCB の外形、穴、銅箔などを再生成 | ソケット生成、コントローラー／センサー生成、分解ビュー設定を内部で順番に呼び出し、最後に `.blend` を保存する |
| [`build_choc_hotswap_sockets.py`](./scripts/build_choc_hotswap_sockets.py) | PCB JSON 内の CPG135001S30 フットプリント | ホットスワップソケットを再生成 | 単独実行時も分解ビューを更新して `.blend` を保存する。PCB 一括生成からも呼ばれる |
| [`build_controller_sensor_modules.py`](./scripts/build_controller_sensor_modules.py) | PCB の配置情報、Auto-KDK とマウスセンサーの寸法・参照情報 | コントローラー、コンスルー、電池／コネクター、マウスセンサー、FPC を再生成 | 既定では分解ビューを更新して `.blend` を保存する。PCB 一括生成からも呼ばれる。`--no-save` と `--no-exploded` を指定可能 |
| [`setup_assembly_exploded_view.py`](./scripts/setup_assembly_exploded_view.py) | 現在の Blender オブジェクトとカスタムプロパティ | 部品を分解レイヤー用 Empty に再分類し、ドライバーを設定 | `.blend` を保存する。`--spacing`、`--assembled`、`--output` を指定可能 |
| [`export_web_glb.py`](./scripts/export_web_glb.py) | 更新済みの `.blend` とマテリアル | 書き出し時だけ組立状態と色を適用 | `.blend` は保存せず、3 個の GLB を出力する。キー刻印の `Legend_*` は出力対象外 |

### PCB 一括生成について

`build_pcb_from_repository.py` は PCB だけのスクリプト名ですが、内部で次も再生成します。

```text
build_pcb_from_repository.py
├── build_choc_hotswap_sockets.py
├── build_controller_sensor_modules.py
└── setup_assembly_exploded_view.py
```

したがって通常の構成同期では `npm run model:pcb` を 1 回実行すれば、PCB、ソケット、コントローラー／センサー、分解レイヤーまで更新されます。ソケットまたはコントローラーだけを調整しているときは、対応する個別コマンドを使えます。

## キーキャップ成果物とBlenderモデル

[`../keycaps`](../keycaps) は、利用者がそのまま3Dプリントしたり、用途に合わせてカスタムしたりできる配布成果物です。Blenderモデルの自動生成依存ではなく、独立した成果物としてバージョン管理します。このため、配布元や生成時のファイル名が変わっても `3d-preview` のスクリプト変更は必要ありません。

現在の [`Surround1x0-AKDK.blend`](./Surround1x0-AKDK.blend) には、今回取り込んだキーキャップ形状が格納済みです。`keycaps/` からBlenderへ再取り込みする常設スクリプトは置かず、将来モデル側も更新するときは、その時点の形状と要件に合わせて作業します。3MFは黒色キーボード向けですが、Blender上の色はマテリアルと `export_web_glb.py` のカラーバリエーションが管理します。

- ハイプロファイルのホーミングは、大西配列の T と O に相当する左右の物理位置 `switch-01-03` に割り当てる。
- ロープロファイルのホーミングは、手前側の外端、つまり左手 DEF と右手 BSP に割り当てる。
- 白黒ともキー刻印は表示しない。Blender 内の `Legend_*` も非表示にし、GLB 書き出し時にも除外する。
- 白ではハイプロファイルのホーミングバーとトラックボールにグレーを使う。
- Web ビューアー上での動的な色切り替えは [`../site/src/main.js`](../site/src/main.js)、書き出し済み Black / White GLB の色は [`export_web_glb.py`](./scripts/export_web_glb.py) が管理する。

## 検証スクリプト

検証スクリプトは `.blend` を更新せず、リポジトリ直下の `.tmp/` に JSON や SVG を生成します。

| 生成対象 | 検証スクリプト | 主な出力先 |
| --- | --- | --- |
| PCB | [`verify_pcb_holes.py`](./scripts/verify_pcb_holes.py) | `../.tmp/pcb-hole-verification/` |
| ホットスワップソケット | [`verify_choc_hotswap_sockets.py`](./scripts/verify_choc_hotswap_sockets.py) | `../.tmp/socket-model/` |
| コントローラー／センサー | [`verify_controller_sensor_modules.py`](./scripts/verify_controller_sensor_modules.py) | `../.tmp/controller-sensor-model/` |

形状生成スクリプトを変更した場合は、最低でも対応する検証スクリプトを再実行します。`build_pcb_from_repository.py` は複数部品を更新するため、PCB、ソケット、コントローラー／センサーの 3 検証を実行します。

## レンダリングとオーバーレイ

次のスクリプト群は、寸法検証を画像で確認するための補助処理です。`render_*.py` は Blender で現在モデルをレンダリングし、対応する `make_*.py` は Pillow を使って参照画像や測定値との比較画像を作ります。

| 対象 | Blender レンダリング | オーバーレイ生成 | 出力先 |
| --- | --- | --- | --- |
| コントローラー／センサー | [`render_controller_sensor_validation.py`](./scripts/render_controller_sensor_validation.py) | [`make_controller_sensor_overlays.py`](./scripts/make_controller_sensor_overlays.py) | `../.tmp/controller-sensor-model/` |
| コントローラーとケース | [`render_controller_case_alignment.py`](./scripts/render_controller_case_alignment.py) | [`make_controller_case_overlays.py`](./scripts/make_controller_case_overlays.py) | `../.tmp/controller-bottom-reference/output/` |
| マウスセンサーとケース | [`render_mouse_sensor_alignment.py`](./scripts/render_mouse_sensor_alignment.py) | [`make_mouse_sensor_alignment_overlays.py`](./scripts/make_mouse_sensor_alignment_overlays.py) | `../.tmp/mouse-sensor-alignment/` |

オーバーレイ生成は、対応するレンダリングと必要な `verify_*.py` の測定 JSON を先に作ってから実行します。`.tmp/` 以下は再生成可能な検証成果物で、編集元データではありません。

## 実行方法

### npm コマンド

Blender の主要コマンドは [`../site/package.json`](../site/package.json) に定義されています。`site` ディレクトリから実行します。

```sh
cd site

npm run model:pcb
npm run model:verify:pcb
npm run model:verify:socket
npm run model:verify:controller
npm run model:export
```

個別更新用に `npm run model:socket` と `npm run model:controller` もあります。`npm run model:sync` は `model:pcb` の後に `model:export` を実行しますが、検証は含みません。

### Blender スクリプトの直接実行

`package.json` にないスクリプトは、リポジトリ直下から次の形式で実行できます。

```sh
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender

"$BLENDER" \
  --background 3d-preview/Surround1x0-AKDK.blend \
  --python-exit-code 1 \
  --python 3d-preview/scripts/verify_pcb_holes.py
```

引数を受け取るスクリプトでは、Blender の引数との境界に `--` を置きます。

```sh
"$BLENDER" \
  --background 3d-preview/Surround1x0-AKDK.blend \
  --python-exit-code 1 \
  --python 3d-preview/scripts/setup_assembly_exploded_view.py \
  -- --spacing 30
```

`build_choc_v2_switches.py` は単体では `.blend` を保存しないため、Blender の Scripting ワークスペースで実行して結果を確認し、明示的に保存してください。

## GLB の出力先

`export_web_glb.py` は、分解ビューのドライバーを一時的に組立状態へそろえ、次を出力します。

| 出力 | 用途 |
| --- | --- |
| [`Surround1x0-AKDK-Black.glb`](./Surround1x0-AKDK-Black.glb) | 黒カラーバリエーションの確認用 |
| [`Surround1x0-AKDK-White.glb`](./Surround1x0-AKDK-White.glb) | 白カラーバリエーションの確認用 |
| [`../site/public/models/surround1x0-akdk.glb`](../site/public/models/surround1x0-akdk.glb) | Web ビューアーが読み込む配信用モデル |

書き出し後は `site` で `npm run build` を実行し、Web 側のモデル読み込みと色切り替えを確認します。

## 更新時のチェックリスト

- 生成物ではなく、対応する設計データまたは生成スクリプトを修正したか。
- 変更した部品に対応する `verify_*.py` を実行したか。
- 新しいオブジェクトを追加した場合、分解レイヤーを再構築したか。
- Black / White / Web の 3 GLB を再出力したか。
- Web 側の色定義も変更した場合、`site/src/main.js` と `export_web_glb.py` の役割の違いを確認したか。
