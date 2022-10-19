# Prompt Creator
　呪文の組み合わせを書くのが面倒なので作成してみた。AUTOMATIC1111/stable-diffusion-webuiのprompts from fileにuploadするためのテキストファイルを生成するcreate_prompt.py。


　組み合わせ爆発に注意。


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