# Jetson Orin Nano セットアップ手順
## Windows + microSD方式

---

# 全体の流れ

## Windows PC側で行うこと

1. JetPackイメージをダウンロード
2. balenaEtcherをインストール
3. microSDへOSを書き込み

## Jetson側で行うこと

4. microSDを挿入
5. 周辺機器を接続
6. 起動
7. Ubuntu初期設定

---

# 【Windows側】1. JetPackイメージをダウンロード

## NVIDIA公式ページ

https://developer.nvidia.com/embedded/jetpack-sdk-62

以下をダウンロード：

- For Jetson Orin Nano Developer Kit currently running JetPack 6.x

⚠️AI情報では、新品未開封品はJetPack 5.1.3をインストール後にファームウェアのアップデートを行い、JetPack 6.xへの移行と誘導される。
　 今回は、ファームフェアが最新状態だったのかJetPack5.1.3では動かずにJetPack6.2で動作した。
　 イメージのバージョンを間違えても壊れることありません。
　 上手く起動しない場合は、別のバージョンで試してください。

---

# 【Windows側】2. balenaEtcher をインストール

## 公式サイト

https://etcher.balena.io/

Windows版をインストール。

---

# 【Windows側】3. microSDへ書き込み

## 必要なもの

- microSDカード
- microSDカードリーダー

---

## 手順

### ① microSDをWindows PCへ接続

カードリーダー経由で接続。

---

### ② balenaEtcherを起動

---

### ③ Flash from file を選択

ダウンロードした以下を選択：

```text
jetson-orin-nano-jp6-sd-card-image.zip
```

※ZIPのままでOK

---

### ④ Select target を選択

microSDカードを選択。

---

### ⑤ Flash! を押す

書き込み開始。

10〜30分程度かかる。

---

# 【Jetson側】4. microSDをJetsonへ挿す

Jetson本体裏面のmicroSDスロットへ挿入。

---

# 【Jetson側】5. 配線

以下を接続：

- モニタ
- キーボード
- マウス
- LANケーブル（推奨）

最後に電源を接続。

---

# 【Jetson側】6. 初回起動

## 電源ON

電源を入れる。

初回起動は数分かかる場合あり。

---

# 【Jetson側】7. Ubuntu初期設定

画面の案内に従って設定：

- 言語
- キーボード
- Wi-Fi
- ユーザー名
- パスワード
- タイムゾーン

設定完了後、Ubuntuデスクトップが起動する。

---

# セットアップ完了

Ubuntu画面が表示されたら成功。
