# 前提条件
- python 3.10以降
# Prompt Creator
　呪文の組み合わせを書くのが面倒なので作成してみた。AUTOMATIC1111/stable-diffusion-webuiのprompts from fileにuploadするためのテキストファイルを生成するcreate_prompt.py。

- 組み合わせ爆発に注意。
- 後ろから順に出てくる仕様になっています
- ```${n}```で括る方法  ```${1},${2},...${100}```
- 変数モードを追加 配列ではなくキーで指定。上から順番にリプレイスするので再帰する場合は、再帰する変数を後で指定すること。指定方法は```${変数名}```　ただし、```${semicolon}```などの予約語は使えません。
- 乱数モードとAPIを利用してループさせると永遠に画像を生成しつづけます

```
usage: create_prompts.py [-h] [--append-dir APPEND_DIR] [--output OUTPUT] input
```

  -h, --help            ヘルプを見る
  
  --append-dir APPEND_DIR    textモード時のappend_dir

  --output OUTPUT       プロンプトファイルの出力先
  
  --json                JSONで出力

  --api-mode            APIの実行(API MODE) --jsonが強制指定される
                        see https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API

  --api-base API_BASE  API MODE設定時のBASEURL 例 http://127.0.0.1:7860

  --api-output-dir API_OUTPUT_DIR API MODEの画像出力先

  --api-input-json API_INPUT_JSON API MODE時にjsonファイルから画像を生成する

  --api-filename-pattern API MODE時のファイル出力パターン　デフォルト [num]-[seed] [num]-[seed]-[prompt]でWeb UIと同じになる。
  　numはシーケンシャル値。Web UIとの違いは、[num]の位置を固定長の変数が前に来る場合、後ろに移動できる設計なのでシーケンシャルにしたい場合、[num]が必須になる点です。

 時間 以下はjobtimestampから計算
- [shortdate] YYMMDD方式 %y%m%d
- [DATE] 古いバージョンのdate。YYYYMMDD %Y-%m-%d
- [year] YYYY
- [month] 01-12
- [day] 01-31
- [time]  hhmmss
- [hour] 00 - 23
- [min] 00-59
- [sec] 00-59
- [datetime] WebUIと同じ YYYMMDDhhmmss %Y%m%d%h%M%s

　上記は[num]の前に配置可能

　　以下は保存時間から計算
- [date] YYYYMMDDでしたが、WebUIとの互換でYYYY-MM-DDに変更 %Y-%m-%d
- [datetime<format>] WebUIと同じ
- [datetime<format><timezone>] WebUIと同じ

 　一応 [prompt_hash] なども使える

- [var] PngInfoで取れる値は一応使えるはず。ただし現在エスケープしないのでnegative promptなどは注意
- [info:var] --info "key1=value1,key2=value2,...." で追加した値を追加
- [command:var] 実行コマンドを追加 例：[command:width] この変数はAPIの返り値ではなく送信値を入れる

--num-once ファイル名の番号チェックを最初の一度しか行いません

--max-number MAX_NUMBER Yaml Modeの option.numberを上書きする

--api-filename-variables Yaml Modeの変数をファイル名に使える様にする（エラーが出やすいので注意）
　

　　例：
```yaml
appends:
    country: append/landscape/c01-countries.txt
```
　の時、[var:country] で国名が追加される e.g. [num]-[seed]-[var:country]


--override "key1=value,key2=value2,...." yamlのcommandの値を上書きする 

--api-set-sd-model API_SET_SD_MODEL SD MODELを変更する　例 e.g. --api-set-sd-model "wd-v1-3.ckpt [84692140]"
  　ハッシュからの変更はまだ実装してない。

--api-set-sd-vae VAEファイルを変更する

　上二つはAPIからのoptionの変更が可能な必要があります。

## Textモード
　promptを書き散らしたTextファイルにリストを並べたappend_dirの下のファイルを読み込ませるスクリプト。置き換える順番は```${1},${2},${3}....```になり、ソートされたファイル名の順に適用される。--append-dirの設定が必要。改行は半角スペースに置き換わる。

例：
```txt
--prompt
"((masterpiece)), (((best quality))), ((ultra-detailed)), ((illustration)), ((disheveled hair)),
,a ${1},${2},girl wearing school uniform in falling cherry blossoms,wind,
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
    prompt: "((masterpiece)), (((best quality))), ((ultra-detailed)), ((illustration)), ((disheveled hair)),a ${1} ${2} girl wearing school uniform in falling cherry blossoms,wind1girl, solo"
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
  仕様上、```${1}```から順番に置き換えていくので、```${1}```のリプレイスを```${2} ${3}```にすることが出来ます。以下の様になります。

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
 -  1番目 ```${var,1}```
 -  2番目 ```${var,2}```
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
- interrogate.py 実装は終了。
- 分割変数のデフォルト値設定
- Overritde Prompt
- versioning
- extension mode
- mix mode
- ネームシードのディレクトリサポート(限定対応)
- API for user authencation
- {= 計算式}