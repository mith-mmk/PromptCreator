# 前提条件
- python 3.10以降
# Prompt Creator
　呪文の組み合わせを書くのが面倒なので作成してみた。AUTOMATIC1111/stable-diffusion-webuiのprompts from fileにuploadするためのテキストファイルを生成するcreate_prompt.py。

- 組み合わせ爆発に注意。
- 後ろから順に出てくる仕様になっています
- リプレイス変数は、$1,$2,...$9の次は$a(10番目)...$zになる
- $\{n\}で括る方法 コチラの方が安全 $\{1\},$\{2\},...$\{100\}
- 変数モードを追加 配列ではなくキーで指定。上から順番にリプレイスするので再帰する場合は、再帰する変数を後で指定すること。指定方法は$\{変数名\}　ただし、$\{semicolon\}などの予約語は使えません。

```
usage: create_prompts.py [-h] [--append-dir APPEND_DIR] [--output OUTPUT] input
```

## Textモード
　promptを書き散らしたTextファイルにリストを並べたappend_dirの下のファイルを読み込ませるスクリプト。置き換える順番は$1,$2,$3....になり、ソートされたファイル名の順に適用される。--append-dirの設定が必要。改行は半角スペースに置き換わる。

例：
```txt
--prompt
"((masterpiece)), (((best quality))), ((ultra-detailed)), ((illustration)), ((disheveled hair)),
,a $1,$2,girl wearing school uniform in falling cherry blossoms,wind,
1girl, solo"
--negative_prompt
"longbody, lowres, bad anatomy, bad hands, missing fingers,
text, error,heart_mark,signature, watermark, username, blurry, artist name
pubic hair,extra digit, fewer digits, cropped, worst quality,
low quality,(((bad hands)))"
--seed 2027904422
```

## yamlモード
　拡張子がyamlもしくはymlの場合 yamlで読み込む

例：配列モード
```yaml
appends:
    -
       - black eyes
       - blue eyes
       - white eyes
    -
       - blonde
       - brown 
       - pink twin-tail
command:
    prompt: "((masterpiece)), (((best quality))), ((ultra-detailed)), ((illustration)), ((disheveled hair)),a $1 $2 girl wearing school uniform in falling cherry blossoms,wind1girl, solo"
    negative_prompt: "longbody, lowres, bad anatomy, bad hands, missing fingers,text, error,heart_mark,signature, watermark, username, blurry, artist namepubic hair,extra digit, fewer digits, cropped, worst quality,low quality,{{{bad hands}}}"
    seed: -1
    width: 640
    height: 448
    cfg_scale: 7.5
```

例：変数モード
```yaml
appends:
    eye:
       - black eyes
       - blue eyes
       - white eyes
    hair:
       - blonde
       - brown 
       - pink twin-tail
command:
    prompt: "((masterpiece)), (((best quality))), ((ultra-detailed)), ((illustration)), ((disheveled hair)),a ${eye} ${hair} girl wearing school uniform in falling cherry blossoms,wind1girl, solo"
    negative_prompt: "longbody, lowres, bad anatomy, bad hands, missing fingers,text, error,heart_mark,signature, watermark, username, blurry, artist namepubic hair,extra digit, fewer digits, cropped, worst quality,low quality,{{{bad hands}}}"
    seed: -1
    width: 640
    height: 448
    cfg_scale: 7.5
```

### 乱数モード

　呪文を自動生成します。

```yaml
version: 0.2  #None impl
options:
#    filename: list.txt  #None impl
    method: random # default= multiple,random, ...
    number: 200    # 出力する数 list limit, "multiple" is not use
    weight: True   # Weight mode = Ture or False default:0.1
    default_weight: 0.1 # None impl 現状、何を指定しても絶対に 0.1
append:
    - 0.2;blue      # weight 0.2
    - 0.3;yellow    # weight 0.3
    - white         # use default 0.1
```

###　再帰置換について
  仕様上、$1から順番に置き換えていくので、$1のリプレイスを$2 $3にすることが出来ます。以下の様になります。

```yaml
append:
    - 
        - ${2} eyes ${3} hair
    -
        - 0.3;blue
        - 0.1;red
        - 0.6;
    -
        - 0.5;blonde
        - 0.5;brown
```

　変数名でも上から順番に適用されるはず（pyyamlの仕様に依存）

### 分割置換
　;で区切ることで一つの変数で複数の値を指定出来ます。このモードは最初にweightが必要になります。
 -  1番目 ${var,1} 
 -  2番目 ${var,2}
 -  以下略

　空白は見ていません。構文解析を実装する局面まで設計しない（関数実装する時になろうかと）

例)
```yaml
     append:
            -
                - 0.5;buldog sourse;dog\;cat
                - 0.5;kagome sourse;bird
```

```yaml
   prompt: "${1,1}"  # <- buldog sourse, kagome sourse
   negative_script: "${1,2}" # <- dog;cat, bird
```

## filenameモード
　変数リストは、yaml内ではなくファイル名で指定可能です。リストを使い回しするときに便利。

```
     append:
            - color.txt
```

- color.txt

\#はコメント
```
# Color リスト
black
white
grey
red
blue
green
```
 スペースで区切ることで複数のファイルを結合できます。

```
     append:
            - color.txt color2.txt
```

- color2.txt
```
purple
yellow
cyan
```

- color.txtとcolor2.txtを結合して利用

### escape
　;は\;もしくは\$\{semicolon\}でエスケープ可能です。

### 書きかけ
- before_multiple:
- append_multiple:

# APIモード
  --api-mode            output api force set --json
                        see https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API

　――を指定すると出力をAPIを実行します。出力は強制的にJSONに変わる。

　APIとFile Prompts from file scriptでは使えるオプションが異なるので注意(例えば、sampler indexはscriptでは数字指定なのに対し、APIは名称指定)





# Issues

- async exceptions traps
- img2img.py  テスト実装の試験中 pngのコメントにpromptが入って居ないとエラー。jpegはexif内に収めるらしいが未実施。
- interrogate.py 実装は終了したが、本体のAPIがバグっている。issue書かないと。BLIPは重いので、Deep Danbooruを呼び出したい。このモードはimg2imgのプロンプトを自動生成したり自動的に弾くのに使える。
- 分割変数のデフォルト値設定
- Overritde Prompt
- versioning
- extension mode
- mix mode