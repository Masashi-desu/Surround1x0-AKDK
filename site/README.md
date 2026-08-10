# Surround1x0-AKDK Three.js Preview

ViteとThree.jsで`3d-preview/Surround1x0-AKDK.blend`のGLBを表示します。

```bash
cd site
npm install
npm run model:sync
npm run dev
```

## 機能

- Black / Warm Ivory / GLB Originalの色表示切替
- 全体、左手側、右手側、PCB基板、Auto-KDKマイコン基板、コンスルーピン、マウスセンサー、ケース、スイッチ、スイッチソケット、キーキャップ、トラックボール、コネクタ表示
- Choc V2茶軸／青軸を内部部品ではなく一式として選べる代表単体表示
- キースイッチ単体表示中の内部パーツExploded View
- ケース上下、ソケット、PCB、コンスルー、マイコン基板、マウスセンサー、スイッチ、キーキャップ、トラックボールのExploded View
- 分解量スライダー、表示対象へのカメラフィット、視点リセット

GLBはBlenderの`exploded_view_layer`と`exploded_view_order`カスタムプロパティを
保持します。スイッチ内部の部品はGLBに含まれますが、WebのExploded Viewでは
スイッチ一式として動きます。表示対象から個別のキースイッチを選択した場合だけ、
「分解」でケース・ステム・ばね・接点などの内部パーツを展開します。

## PCBからプレビューへの反映

`pcb/Surround1x0-AKDK-left-pcb.json`と
`pcb/Surround1x0-AKDK-right-pcb.json`を元に、基板外形、配線、露出パッド、
シルクと実際に貫通したドリル穴を持つベアPCBをBlenderへ再生成します。
EasyEDAの`HOLE`と多層`PAD`のドリル値は半径として読み取り、直径へ変換してBoolean加工します。
マイコン接続用フットプリントのスルーホールとパッドはPCB側に残し、Auto-KDK基板、
9ピン×2列のコンスルー、LiPoはそれぞれ独立ジオメトリとして配置します。
右手側には13.4 × 7.4 mmのPAW3222マウスセンサー基板と0.5 mmピッチ6ピンFPCも配置します。
スイッチソケットはCPG135001S30のデータシート寸法とEasyEDAの実穴位置を元に、
PCBとは別の独立パーツとして45個配置します。ダイオードは引き続きPCBモデルには
含めず、独立パーツとして追加できる構成です。

```bash
cd site
npm run model:sync
```

`model:sync`はBlenderファイルを更新してから、サイト用GLBを再出力します。

穴加工をEasyEDAの元データと照合する場合は、次を実行します。

```bash
npm run model:verify:pcb
npm run model:verify:socket
npm run model:verify:controller
```

検証結果は`.tmp/pcb-hole-verification/`へ出力され、参照穴と生成メッシュの
全体／拡大オーバーレイ、および中心・直径誤差のJSONを確認できます。
ソケットの寸法・ボス径・PCB穴中心との位置合わせは`.tmp/socket-model/`へ
オーバーレイと測定JSONを出力します。
Auto-KDK基板、コンスルーピン、マウスセンサー、FPCの寸法・配置検証は
`.tmp/controller-sensor-model/`へ測定JSON、レンダー、参照写真オーバーレイを出力します。

## GitHub Pagesへのデプロイ

`main`ブランチへのpushで`site/**`に変更が含まれる場合、
`.github/workflows/deploy-site-pages.yml`がViteをビルドしてGitHub Pagesへデプロイします。
Actionsタブから手動実行することもできます。

初回のみ、GitHubの「Settings → Pages → Build and deployment → Source」で
`GitHub Actions`を選択してください。PagesのベースパスはWorkflowからViteへ自動的に渡されます。
