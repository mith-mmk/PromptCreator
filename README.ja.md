# Prompt Creator
　呪文の組み合わせを書くのが面倒なので作成してみた。AUTOMATIC1111/stable-diffusion-webuiのprompts from fileにuploadするためのテキストファイルを生成するcreate_prompt.py。

- 組み合わせ爆発に注意。
- 後ろから順に出てくる仕様になっています
- ~~リプレイス変数は、$1,$2,...$9の次は$a(10番目)...$zになる~~ 2022/11/01 廃止
- \$\{n\}で括る \$\{1\},\$\{2\},...\$\{100\}
- yamlモードに変数モードを追加 配列ではなくキーで指定。上から順番にリプレイスするので再帰する場合は、再帰する変数を後で指定すること。指定方法は\$\{変数名\}　ただし、\$\{semicolon\}などの予約語は使えません。

```
usage: create_prompts.py [-h] [--append-dir APPEND_DIR] [--output OUTPUT] [--json [JSON]] [--api-mode [API_MODE]] [--api-base API_BASE]
                         [--api-output-dir API_OUTPUT_DIR]
                         input
```

--json JSONで出力
--api-mode 実行結果をAPIで叩きに行きます。Web UIを--APIで起動している必要有り。
--api-base API_BASE APIを実行するホスト名(例:http://127.0.0.1:7860) 参考:　https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API
--api-output-dir イメージを出力するフォルダを指定します(未指定の場合は、./outputs)


# 準備
 Python 3.10+(3.8でも恐らく動く)。以下のパッケージをインストール。

```
pip install pyyaml
pip install Pillow
pip install httpx
```

# 使い方
## Textモード
　promptを書き散らしたTextファイルにリストを並べたappend_dirの下のファイルを読み込ませるスクリプト。置き換える順番は$1,$2,$3....になり、ソートされたファイル名の順に適用される。コマンドラインに--append-dirの設定が必要。改行は半角スペースに置き換わる。


実行例：
```
./create_promopts.py prompt.txt --append_dir ./append --output list.txt
```

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

実行例：
```
./create_promopts.py prompt.yml --output list.txt
```

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
version: 0.2  #Version is Not implement 
options:
#    filename: list.txt  #Not implement
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
  仕様上、上から順番に置き換えていくので、\$\{1\}のリプレイスを\$\{2\} \$\{3\}にすることが出来ます。以下の様になります

```yaml
append:
    - # ${1}
        - ${2} eyes ${3} hair
    -
        - 0.3;blue
        - 0.1;red
        - 0.6;
    -
        - 0.5;blonde
        - 0.5;brown
```


### エスケープ
 エスケープは;の置き換えに\\;が利用できます。もしくは\$\{semicolon\}

### 分割置換と 置換

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

### filenameモード
　テキストファイル名から読み込ませます。パスは実行パスからの相対パスになります。ファイルは;で区切ること。中身は変則的なcsv(セミコロン区切り)になります。#で始まる行はスキップします。


```yaml
     append:
            - color.txt
```

例:color.txt
```
# Color リスト
0.5;black
white
grey
red
blue
green
```

# issue
- img2img
- Prompt上書きモード
- バージョニング