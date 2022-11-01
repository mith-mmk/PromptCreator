# Prompt Creator
　呪文の組み合わせを書くのが面倒なので作成してみた。AUTOMATIC1111/stable-diffusion-webuiのprompts from fileにuploadするためのテキストファイルを生成するcreate_prompt.py。

- 組み合わせ爆発に注意。
- 後ろから順に出てくる仕様になっています
- リプレイス変数は、$1,$2,...$9の次は$a(10番目)...$zになる
- $\{n\}で括る方法 コチラの方が安全 $\{1\},$\{2\},...$\{100\}

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

例：
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
  仕様上、$1から順番に置き換えていくので、$1のリプレイスを$2 $3にすることが出来ます。以下の様になります

```yaml
append:
    - 
        - $2 eyes $3 hair
    -
        - 0.3;blue
        - 0.1;red
        - 0.6;
    -
        - 0.5;blonde
        - 0.5;brown
```


# issues
- yaml's append list reading from txt file
- append内でセミコロンを使いたい時のエスケープ　\\;
- 分割置換と$\{0\} 置換
    例)
```
     append:
            \-
                \- 0.5;buldog sourse;dog\;cat
                \- 0.5;kagome sourse;bird
```

```
   prompt: "$\{1,1\}"  <- buldog sourse, kagome sourse
   negative_script: "$\{1,2\}" <- dog;cat, bird
```

- filenameモード
```
     append:
            \- color.txt
```

color.txt
```
# Color リスト
black
white
grey
red
blue
green
```
