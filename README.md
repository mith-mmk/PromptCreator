# Create prompt V2
  Create prompt V2 は AUTOMATIC1111/stable-diffusion-webui のためのプロンプト作成ツールです（日本語と英語の両方記述することにしました）

  Create prompt V2 is a prompt creator for AUTOMATIC1111/stable-diffusion-webui

# enviroment(環境)
- AUTOMATIC1111/stable-diffusion-web-ui (最新のバージョン) のAPIを有効にする
  - --APIオプションを追加する
-　python 3.10以降 

- automatic1111/stable-diffusion-web-ui (newest commit) enable remote access 
  - add webui --API option
- python 3.10 and later

# Usage(使い方)
```
usage: cp2.py [-h] [--append-dir APPEND_DIR] [--output OUTPUT] [--json [JSON]] [--api-mode [API_MODE]]
              [--api-base API_BASE] [--api-userpass API_USERPASS] [--api-output-dir API_OUTPUT_DIR]
              [--api-input-json API_INPUT_JSON] [--api-filename-pattern API_FILENAME_PATTERN]
              [--max-number MAX_NUMBER] [--num-length NUM_LENGTH]
              [--api-filename-variable [API_FILENAME_VARIABLE]] [--json-verbose [JSON_VERBOSE]]
              [--num-once [NUM_ONCE]] [--api-set-sd-model API_SET_SD_MODEL] [--api-set-sd-vae API_SET_SD_VAE]       
              [--override [OVERRIDE ...]] [--info [INFO ...]] [--save-extend-meta [SAVE_EXTEND_META]]
              [--image-type IMAGE_TYPE] [--image-quality IMAGE_QUALITY] [--api-type API_TYPE]
              [--interrogate INTERROGATE] [--alt-image-dir ALT_IMAGE_DIR] [--mask-dirs MASK_DIRS]
              [--mask_blur MASK_BLUR] [--profile PROFILE] [--debug [DEBUG]] [--v1json [V1JSON]]
              [input]
```

  -h, --help            show this help message and exit(ヘルプ表示)

  --append-dir APPEND_DIR
                        direcory of input append prompt files(追加プロンプトファイルのディレクトリ)

  --output OUTPUT       direcory of output file of prompt list file(プロンプトリストファイルの出力ディレクトリ)

  --json                output JSON(JSONで出力する,デフォルトはtextでWeb UIのprompt matrixに貼り付け用 )

  --v1json              output V1 JSON(旧バージョンのJSONで出力する)

  --profile PROFILE     switch profile in config file(設定ファイルのプロファイルを切り替える)
  
  --debug               debug mode(デバッグモード)

  --json-verbose        output verbose in JSON(replace --api-filname-variable)(JSONで詳細を出力する)

  --api-mode            output api force set --json(APIを呼び出し、自動実行する)
                        see https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API

  --api-base API_BASE  for call api from this script e.g. http://127.0.0.1:7860 (APIを呼び出すためのベースURL)

  --api-output-dir API_OUTPUT_DIR
                        api output images directory(APIの出力画像ディレクトリ)

  --api-input-json API_INPUT_JSON
                        api direct inputs from a json file(APIの直接入力用のjsonファイル)

  --api-filename-pattern API_FILENAME_PATTERN
                        api outputs filename pattern default: [num]-[seed] (APIの出力ファイル名パターン 既定値: [num]-[seed])

  --max-number MAX_NUMBER
                        override option.number for yaml mode(出力数。コンフィグの設定を上書きする)

  --api-filename-variables [API_FILENAME_VARIABLES]
                        replace variables use filename(ファイル名に変数を使う)

  --api-set-sd-model SD_MODEL
                        Change sd model "Filename.ckpt [hash]" e.g. "wd-v1-3.ckpt [84692140]" or 84692140 (SDモデルを変更する 例: "wd-v1-3" または 84692140)

  --api-set-sd-vae VAE_FILE
                        set vaefile(include extention) (VAEファイルを設定する。拡張子は省略できません)

  --override
                        command oveeride ex= "width=768, height=1024"(コマンドを上書きする 例: "width=768, height=1024")

  --info
                        add infomation ex="date=2022/08/19, comment=random"(情報を追加する 例: "date=2022/08/19, comment=random")

  --save-extend-meta
                        save extend meta data using for create_prompt(拡張メタデータを保存する create_promptで使用する)

  --image-type
                        image type jpg or png/ default png(画像タイプ jpg または png デフォルトはpng)

  --image-quality
                        default 80, image quality for jpg(デフォルト80、jpgの画質)
                            
## Compatibility(互換性)
    - V2 is not compatible with V1(旧バージョンとの互換性はありません)

# Installation(インストール)
```
pip install pyyaml
pip install Pillow
pip install httpx
```
# yamlモード(textモードは廃止になりました)

## V1との違い
- only variable mode(変数モードのみ)
- appends is obsolete(appendsは廃止になりました)
  - change variables and array (variablesとarrayに変更)
- enable associative array(連想配列をサポートしました)
- enable jsonl read for list file(jsonlの読み込みが可能になりました)
- category query for jsonl(カテゴリークエリーが可能になりました)
- variables nest is max 10, ignore define order(変数のネストは最大10, 定義の順番は関係ありません)
## 書き方
- random is generate random prompt(randomはランダムプロンプトを生成します)
- multiple is generate multiple prompt(multipleは配列から複数のプロントを作成します)
- cleanup is clean up prompt(cleanupはプロンプトをクリーンアップします)

```yaml
version: 2          # must(必須)
options:
#   sd_model: anythingV5Anything_anythingV5PrtRE
#   sd_vae: kl-f8-anime2-vae.safetensors
    output: ./outputs/v2.json
    json: true
    number: 10   # number of prompt(プロンプトの数) multipleの場合は配列数がかけ算される
methods:  # random: 1  or multiple: array
    - multiple: char place # array char と place から複数のプロンプトを生成
    - random 0 # random 0 is default(ランダム0はデフォルト)
    - creanup prompt # clean up prompt (promptをクリーンアップ)
variables:
    actions:
        - standing
        - sitting
    date: jsonl/date.jsonl[animal] # jsonl file and category query(カテゴリークエリー)
    
array:
    char: [cat, dog, bird, fish]
    place: [room, garden, park, street]
command:
    prompt: "${char} is ${actions} in ${place}, ${date}" # prompt command(プロンプトコマンド)
    negative_prompt: "negative prompt"
    seed: -1        # -1 is random seed(-1はランダムシード)
    width: 640      # width of image(画像の幅)
    height: 448     # height of image(画像の高さ)
    cfg_scale: 7.5  # scale of image(画像のスケール)
    # それ以外はapiのマニュアルを参考にしてください
```
 This case is generate 10 * 4 * 4 = 160 prompts, beacuse multiple mode uses char number is and place number 4. (この場合、160のプロンプトが生成されます。multipleモードでcharが4つ、placeが4つ指定されているため10 * 4 * 4 = 160になります。)

### 配列変数
```yaml
    char: 
        - 0.1;cat;dog;bird;fish
    cat: ${char[1]}
    dog: ${char[2]}
    bird: ${char[3]}
    fish: ${char[4]}
```
array variables can set weight at first of array. In this case, char has array of cat, dog, bird, fish with weight 0.1. cat, dog, bird, fish are replaced to 1st to 4th of char array. (配列変数は、配列の最初に重みを指定することができます。この場合、charは0.1の重みでcat、dog、bird、fishの配列を持ちます。cat、dog、bird、fishはcharの配列の1から4番目に置き換えられます。)

### nested variables(ネスト変数)
```yaml
    char: 
        - ${animal}
        - ${human}
    animal: [cat, dog, bird, fish]
    human: [girl,boy]
```
This case is replace char to \$\{animal\} and \$\{human\} (この場合、\$\{char\}が\$\{animal\}と\$\{human\}に置き換えられます)

### ファイルの読み込み
#### text
```yaml
    date: text/date.txt
```
This case is read text file date.txt. (この場合、date.txtファイルを読み込みます)
```text
0.1;day
0.1;night
```
textではクエリーと連想配列はサポートされていません

#### jsonl
```yaml
    date: jsonl/date.jsonl[animal]
```
This case is read jsonl file date.jsonl and query category animal. (この場合、date.jsonlファイルを読み込み、カテゴリーanimalをクエリします)
```jsonl
{"W":0.1, "C":["animal"], V:"day", animal:"cat"}
{"W":0.1, "C":["animal"], V:"day", animal:"dog"}
{"W":0.1, "C":["animal"], V:"night", animal:"bird"}
{"W":0.1, "C":["animal"], V:"night", animal:"fish"}
{"W":0.1, "C":["*"], V:"moonnight", animal:"bird"} // * is wlde card (*はワイルドカードです)
{"W":0.1, "C":["animal","human"], V:"night", animal:"human"} // multiple category(複数のカテゴリー)
{"W":0.1, "C":["insect"], V:"night", animal:"ant"} // not query(クエリーされない)
```
shortcut W=weight, C=category, V=variables(W,C,Vはweight, category, variablesのショートカットです) V can be array or string(Vは配列または文字列になります)

This case is suppot query and associative array(このケースで連想配列がサポートされています)

Example(例)
```yaml
    variables:
        actions:
            - standing
            - sitting
        all: jsonl/all.jsonl # all category(全てのカテゴリー)
        date: jsonl/date.jsonl[animal] # category query(カテゴリークエリー)
        day: ${date} # variable = ${date[1]}
        animal: ${date["animal"]} # associative array(連想配列)
        beings: jsonl/date.jsonl[animal,human] # multiple category(複数のカテゴリー) saparated by comma(カンマで区切る) not support space(スペースはサポートされません)
```
#### パーサー
 sentence in \$\{ \} can be parsed(\$\{= \}の中に式が書けます)

Example(例)
```yaml
    seed: ${=random_int()} # random seed(ランダムシード)
    width: ${=int(${size}) * 2} # width = size * 2(幅 = サイズ * 2)

```
#### current functions(現在の関数)
no debug(デバッグしていません)

functions(関数) str1,str2,.. are string(文字列) and x,y... are number(数値)
- pow(x,y) : x^y
- sqrt(x) : square root(平方根)
- abs(x) : absolute value(絶対値)
- ceil(x) : round up(切り上げ)
- floor(x) : round down(切り捨て)
- round(x) : round(四捨五入)
- trunc(x) : truncate(切り捨て)
- int(str1) : string to integer(文字列を整数に変換)
- float(str1) : string to float(文字列を浮動小数点に変換)
- str(x) : number to string(数値を文字列に変換)
- len(str1) : length of string(文字列の長さ)
- max(x,y), max(str1,str2) : max number(最大値)
- min(x,y), min(str1,str2) : min number(最小値)
- replace(str1,str2,str3) : replace str2 to str3 in str1(文字列str1の中のstr2をstr3に置換)
- split(str1,str2) : split str1 by str2(文字列str1をstr2で分割)
- upper(str1) : upper case(大文字)
- lower(str1) : lower case(小文字)
- if(condition, truecase, falsecase) : if condition is true, return truecase, else return falsecase(ifのconditionがtrueの場合、truecaseを返し、それ以外はfalsecaseを返します)
- not(condition) : 0 to 1, 1 to 0(0を1に、1を0に変換)
- and(condition1, condition2) : and operation(論理積)
- or(condition1, condition2) : or operation(論理和)
- match(str1,str2) : match str1 to str2(文字列str1がstr2に一致)
- substring(str1, start, end) : substring of str1(文字列str1の部分文字列)
- random(start, end) : random integer number(ランダムな整数) or random float number(ランダムな浮動小数点数)
- random_int(): random integer number(ランダムな整数) 0 - 2^64 -1
- random_float(): random float number(ランダムな浮動小数点数) 0 - 1
- random_string(len): random string(ランダムな文字列) len characters
- uuid(): random uuid(ランダムなuuid)
- time(): current time(現在時刻)
- date(): current date(現在日付)
- datetime(): current datetime(現在日時)
- timestamp(): current timestamp(現在のタイムスタンプ)
- year(): current year(現在の年)
- month(): current month(現在の月)
- day(): current day(現在の日)
- hour(): current hour(現在の時)
- minute(): current minute(現在の分)
- second(): current second(現在の秒)
- weekday(): current weekday(現在の曜日)
- week(): current week(現在の週)

# V1(旧バージョン)
 see [READMEV1.md](READMEV1.md)