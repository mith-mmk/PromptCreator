# Create prompt V2
  Create prompt V2 は AUTOMATIC1111/stable-diffusion-webui のためのプロンプト作成ツールです(定義ファイルを作るUIも作らないと)

  Create prompt V2 is a prompt creator for AUTOMATIC1111/stable-diffusion-webui

## objective(目的)
 The Prompt Creator V2 is a prompt creator for AUTOMATIC1111/stable-diffusion-webui(Profileから、Stable Diffusion用のプロンプトを自動作成します)
 You can also automatically generate images by using the API.(またAPIを叩くことにより画像の自動生成を可能にします)

 - A config file is required(設定ファイルが必要です)
 - A config file is written in yaml(設定ファイルはyaml形式で記述します)
 - A config file is create prompt list file(設定ファイルはプロンプトリストファイルを作成します)
 - A config file has methods, number of prompt, prompt command, prompt settings(設定ファイルには、メソッド、プロンプトの数、プロンプトコマンド、プロンプト設定が記述されます)
 - A config file has variables, array, command, profiles, but can write in json or text(設定ファイルには、変数、配列、コマンド、プロファイルが記述されますが、jsonまたはテキストで記述できます)
 - See examples for details(詳細はexamplesを参照してください)

input.yaml
```yaml
version: 2.0  # must(必須)
options:
    output: ./outputs/v2/girls.json # output file(出力ファイル)
    json: true # output json(jsonで出力)
    number: 50   # number of prompt(プロンプトの数)
methods:  # random: 1  or multiple: array
    - random: 0 # random 0 is use options.number(0はoptions.numberを使用) randam is generate random prompt(randomはランダムプロンプトを生成します)
    - cleanup: prompt negative_prompt # clean up prompt (promptをクリーンアップします)

variables:  # variables(変数)
    negative: ['nsfw, easynegative']  # If you define variables in the config, define them as an array(config内に変数を定義する場合は配列で定義します)
    actions: $json/actions.jsonl      # actions(アクション)
    outfits: $jsonl/outfits.json  # outfits(服)
    place: $jsonl/places.jsonl[places] # place(場所)

    eyes: $jsonl/eyes.jsonl[eyes] # ${eyes} 目
    hair: $jsonl/hairs.jsonl[hair] # ${hair} 髪
    
command:  # prompt command(プロンプトコマンド) The content that will be output to the file(ファイルに出力される内容になります)
    prompt: "${eyes} ${hair} girl wearing ${outfits} is ${actions} ${place} " # prompt command(プロンプトコマンド)
    negative_prompt: "${negative}"
    seed: -1
    width: 512
    height: 512
    steps: 20
    cfg_scale: 7.5
    sampler_name: DPM++ SDE
    batch_size: 1  # if you can use n size batch
    n_iter: 1 # also same butch count
# higher.fix
    enable_hr: true
    hr_scale: 2
    hr_upscaler: R-ESRGAN 4x+ Anime6B
    denoising_strength: 0.5
    hr_second_pass_steps: 10
    override_settings:        # override settings(設定を上書き)
        CLIP_stop_at_last_layers: 2               # CLIP stop at last layers(CLIPを停止する階層を指定、2を推奨するケースが多い)
```

jsonl(eyes.jsonl)
```jsonl
/* 
  If you want write comment in jsonl, you can it.(jsonl内でコメントを書く場合は、このようにします)
*/
// You can write like this(これでも可能です)
{"W": 0.1, "C": ["eyes"], "V": "blue eyes"} // W C V is upper case(W C Vは大文字)
{"W": 0.1, "C": ["eyes"], "V": "green eyes"}
{"W": 0.1, "C": ["eyes"], "V": "black eyes"}
{"W": 0.1, "C": ["eyes"], "V": "brown eyes"}
{"W": 0.1, "C": ["eyes"], "V": ["red eyes"]}  // "V" is string or string array("V"は文字列または文字列配列)
```

You can write text file(semiclon separated), but cannot write category (テキスト(セミコロン区切り)でも書けまが、カテゴリーは書けません)

eyes.txt
```text
0.1;blue eyes
0.1;green eyes
0.1;black eyes
0.1;brown eyes
0.1;red eyes
```

## 実行方法(How to run)
```
python cp2.py input.yaml
```

You can call API and generate images automatically by adding options(オプションを追加することで、APIを呼び出し画像を自動生成することができます)
You need to add --api and --listen options to WebUI(ただし、WebUIに--apiと--listenオプションを追加する必要があります)

If you use "Prompts from file or textbox" in WebUI, output in text format. If you call API, output in JSON format(WebUIの"Prompts from file or textbox"を使う場合はtext形式で出力します。APIを叩く場合はJSON形式で出力します)


Outputs of examples(以下は、exampleの実行結果です)
```
python .\cp2.py .\examples\prompts-girls.yaml
```

Outputs
```txt
--prompt (petite kawaii girl) wearing (yellow camisor), normal yellow eyes, annoyed, brown curly twin-tail hair between eyes shiny long hair, (medium breasts) 2girls are serving dish, diorama style (hiten_1, Production I.G), on the fantasy field in the day, steam, (blur), (flock of birds), from side --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (teenage girl) wearing (check pink t-shirt and black denim shorts), white grove, garter belt and knee sox, mole under eye white eyes, embarrassed, light orange wavy triple bun twin-tail dyed bangs short hair, (large breasts) 1girl is claw pose, super-deformed (tony_taka, grisaia_\(series\)), in the bus, vanishing point, long shot, from below --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (teenage girl) wearing (white swim shirt and tight pants), normal green eyes, frown, pink straight flipped shiny medium hair, (small breasts) 2girls are back-to-back, anime_screencap (Production I.G, Charlie Bowater), on the poolside, (sharp focus), from below --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (teenage girl) wearing (floral print black long skirt maid uniform with white apron and white hairband), normal grey eyes, excited, light grey straight hair between eyes shiny medium hair, (small breasts) 1girl is falling from sky, super-deformed (kantoku_\(style\), Unfairr), in the jinja shrine, (feathers effect), from side --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (teen cute girl) wearing (geometric pattern helloween dress, GhostWhite rose motif hair ornament), check brown cap, camouflage emerald green chocar, normal emerald green eyes, nose blush, light orange straight single braid shiny short hair, (medium breasts) 6girl+ are dancing, thick outline, black outline (Ufotable, violet_evergarden), in the temple, (spot light) --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (milf wife) wearing (black sweater dress), lemon print green cap, normal pink eyes, light smily, white straight side braid hair over one eye very short hair, (pointy breasts) 1girl opens a door, super-deformed (pixiv, kantoku_\(style\)), in the buddest temple in the day, motion lines, (confetti) --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (teen cute girl) wearing (space print BlueViolet t-shirt and twotone microskirt), normal light blonde, eye reflection eyes, frown, purple straight twin-tail hair over shoulder hair, (medium breasts) 2girls are sweaping, super-deformed (Yuumei, momoco_\(momoco_haru\)), in the office room, trembling, full shot --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (house wife) wearing (morning glory print silver tied shirt and pink pencil skirt on FireBrick jacket), normal brown, closed eyes eyes, jitome, white straight sidelocks twin-tail shiny floating long hair, (flat chests) 1girl is hand in own leg, game_cg (RossDraws, minori), in the school, (faint light), medium shot, from above --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (curte slender girl) wearing (argylec white negligee, hair flower), camouflage gray boots, normal orange, closed one eye eyes, sleepy, blonde straight single hair bun very short hair, (medium breasts) 1girl is v sign, Lego style (egami, pixiv), in row of cherry blossom trees, (sharp focus), (breeze), full shot --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
--prompt (teenage girl) wearing (white blazer and uniform), normal silver eyes, doyagao, orange straight twin-tail dyed bangs very long hair, (medium breasts) 1girl is standing up, super-deformed (RossDraws, yuzusoft), in Taipei blue sky, wet, dynamic angle, medium shot --negative_prompt nsfw, easynegative, ${doing, 2}, pixel_art, halftone, multiple views, monochrome, futanari, futa, yaoi, speech bubble, (low quality, worst quality:1.4), text, blurry, bad autonomy --seed -1 --width 512 --height 704 --steps 30 --cfg_scale 12.5 --sampler_name DPM++ SDE --batch_size 1 --n_iter 1
```

Outputs of text style use copy and paste on Web UI(text形式の出力はWeb UIに貼り付けて使います)


APIを叩く場合はJSON形式で出力します
```
python cp2.py input.yaml --json
```

You can write in config file, too(設定ファイルに直接記述することもできます)
```yaml
options:
    json: true
```


You can direct run Web UI API(直接実行可能です)
```
python cp2.py input.yaml --api-mode --api-base http://localhost:7860 --api-output ./outputs/text-images --api-filename-pattern [num]-[seed]
```

If you run from JSON file, use --input-json option(JSONファイルを実行する場合は、--input-jsonを使います)
```
python cp2.py --input-json "./outputs/examples.json" --api-output ./outputs/text-images --api-filename_pattern [DATE]-[num]-[seed]
```


# enviroment(環境)
- AUTOMATIC1111/stable-diffusion-web-ui (最新のバージョン) のAPIを有効にする
  - --APIオプションを追加する
  - リモートから実行する場合は、リモートアクセスを有効にする
  - settingを変更できるようにする(overrideを使う場合)
-　python 3.10以降 

- automatic1111/stable-diffusion-web-ui (newest commit) enable remote access 
  - add webui --API option
- python 3.10 and later

# Usage(使い方)
```
usage: cp2.py [-h] [--append-dir APPEND_DIR] [--output OUTPUT] [--json [JSON]] [--api-mode [API_MODE]] [--api-base API_BASE] [--api-userpass API_USERPASS]
              [--api-output-dir API_OUTPUT_DIR] [--api-input-json API_INPUT_JSON] [--api-filename-pattern API_FILENAME_PATTERN] [--max-number MAX_NUMBER]
              [--num-length NUM_LENGTH] [--api-filename-variable [API_FILENAME_VARIABLE]] [--json-verbose [JSON_VERBOSE]] [--num-once [NUM_ONCE]]
              [--api-set-sd-model API_SET_SD_MODEL] [--api-set-sd-vae API_SET_SD_VAE] [--override [OVERRIDE ...]] [--info [INFO ...]]
              [--save-extend-meta [SAVE_EXTEND_META]] [--image-type IMAGE_TYPE] [--image-quality IMAGE_QUALITY] [--api-type API_TYPE] [--interrogate INTERROGATE]
              [--alt-image-dir ALT_IMAGE_DIR] [--mask-dirs MASK_DIRS] [--mask-blur MASK_BLUR] [--profile PROFILE] [--debug [DEBUG]] [--verbose [VERBOSE]]
              [--v1json [V1JSON]] [--prompt [PROMPT]] [--json-escape [JSON_ESCAPE]]
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

  --api-filename-variable
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
                            
  --debug
                        debug mode(デバッグモード)
  --verbose
                        verbose(詳細モード)
  --prompt
                        output prompt only(プロンプトのみ出力する)
  --json-escape
                        multibyte escaped json(マルチバイトをエスケープしたjsonを出力する)

  --api-comfy
                        use comfyui api alternative to webui(Automatic1111ではなくComfyUIのAPIを使う。portが変わるため明示的なhostnameの指定が必要)
  --api-comfy-save      save image directory for comfyui api(ComfyUIのAPI画像を保存先)
                        ui = ComfyUI server, save = save to local, both = both(ComfyUIサーバーの保存先に保存、ローカルに保存、両方)
                        Meta data is converted to Automatic1111 compatible only when save is specified(メタデータはsaveを指定したときのみAutomatic1111互換に変換しようと試みます)

## Compatibility(互換性)
    - V2 is not compatible with V1(旧バージョンとの互換性はありません)

# Installation(インストール)

    - python 3.10 and later is required(3.10以降が必要です)


install required packages(必要なパッケージをインストール)
```
pip install -r requirements.txt
```
# yaml mode

text mode is obsolete(textモードは廃止になりました)
-　yaml mode is create prompt list file from yaml file(yamlモードはyamlファイルからプロンプトリストファイルを作成します)

## difference from V1(V1との違い)
- only variable mode(変数モードのみ)
- appends is obsolete(appendsは廃止になりました)
  - change variables and array (variablesとarrayに変更)
- multipe, aftermultipe is obsolete(multipe, aftermultipeは廃止になりました)
  - change methods (methodsに変更)
- enable associative array(連想配列をサポートしました)
- enable jsonl read for list file(jsonlの読み込みが可能になりました)
- category query for jsonl(カテゴリークエリーが可能になりました)
- variables nest is max 10, ignore define order(変数のネストは最大10, 定義の順番は関係ありません)

## method(メソッド)
- random is generate random prompt(randomはランダムプロンプトを生成します)
- multiple is generate multiple prompt(multipleは配列から複数のプロントを作成します)
- cleanup is clean up prompt(cleanupはプロンプトをクリーンアップします)
- default is random 0(defaultはランダム0です)

```yaml
version: 2          # must(必須)
options:
    output: ./outputs/v2.json
    json: true
    number: 10   # number of prompt(プロンプトの数) multipleの場合は配列数がかけ算される
methods:  # random: 1  or multiple: array
    - multiple: char place # array char と place から複数のプロンプトを生成
    - random: 0 # random 0 is use options.number(0はoptions.numberを使用)
    - creanup: prompt # clean up prompt (promptをクリーンアップ)
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

### array variables(配列変数)
```yaml
    char: 
        - 0.1;cat;dog;bird;fish
    cat: ${char[1]} # array is start 1, zero is not support(配列は1から始まります)
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
    "animal": [cat, dog, bird, fish]
    human: [girl,boy]
```
This case is replace char to \$\{animal\} and \$\{human\} (この場合、\$\{char\}が\$\{animal\}と\$\{human\}に置き換えられます)

### attribute, associative array(アトリビュート,連想配列)
  reserved words are  "W", "C", "V", "weight", "choice", "variable", "query", these are not accesible. (以上は予約語で、アクセス出来ません)

```yaml
    char: 
        - ${being["V"]}   # NG
        - ${being["W"]}   # NG
        - ${being["C"]}   # NG
        - ${being["weight"]}   # NG
        - ${being["choice"]}   # NG
        - ${being["variable"]}   # NG
        - ${being["query"]}   # half OK
        - ${being["animal"]}   # OK
        - ${being["size"]}   # OK
        - ${=query{"being", "animal"}}   # use "query"

    being: jsonl/being.jsonl[animal,human]
```

jsonl file(beings.jsonl)
```jsonl
{"W":0.1, "C":["animal"], "V":"day", "animal":"cat", size:"small"}
{"W":0.1, "C":["animal"], "V":"day", "animal":"dog", size:"big"}
{"W":0.1, "C":["animal"], "V":"night", "animal":"bird", size:"small"}
{"W":0.1, "C":["animal"], "V":"night", "animal":"fish", size:"big"}
```

```yaml
    being: jsonl/being.jsonl[animal]
    "animal": ${being["animal"]}
    size: ${being["size"]}
```

 issue #1 nseted associative array is not supported(入れ子の連想配列はサポートされていません)

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
text is not support query and associative array(textではクエリーと連想配列はサポートされていません)

#### jsonl
```yaml
    date: jsonl/date.jsonl[animal]
```
This case is read jsonl file date.jsonl and query category animal. (この場合、date.jsonlファイルを読み込み、カテゴリーanimalをクエリします)
```jsonl
{"W":0.1, "C":["animal"], "V":"day", "animal":"cat"}
{"W":0.1, "C":["animal"], "V":"day", "animal":"dog"}
{"W":0.1, "C":["animal"], "V":"night", "animal":"bird"}
{"W":0.1, "C":["animal"], "V":"night", "animal":"fish"}
{"W":0.1, "C":["*"], "V":"moonnight", "animal":"bird"} // * is wlde card (*はワイルドカードです)
{"W":0.1, "C":["animal","human"], "V":"night", "animal":"human"} // multiple category(複数のカテゴリー)
{"W":0.1, "C":["insect"], "V":"night", "animal":"ant"} // not query(クエリーされない)
{"weight":0.1, "category":["insect"],  "variable":"night", "animal":"ant"} // same as above(上と同じ)
```
"W","C","V" are shortcuts "weight", "category", "variable" (W,C,Vはweight, category, variablesのショートカットです) V can be array or string(Vは配列または文字列になります)

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
        "animal": ${date["animal"]} # associative array(連想配列)
        beings: jsonl/date.jsonl[animal,human] # multiple category(複数のカテゴリー) saparated by comma(カンマで区切る) not support space(スペースはサポートされません)
```
#### DB query
 issue #2 DB query is not supported, yet (DBクエリーはまだサポートされていません)

```yaml
options:
    db: true
database:
    db: sqlite3 # [sqlite3, mysql, postgresql, mongodb]
    db_connection: db/date.sqlite3  # db connection(データベース接続)
variables:
    date: date[category = `animal`] # select * from date where category = `animal`'
```

### profile(プロファイル)
profile is override config file(設定ファイルをprofileで上書きします)
```yaml
command:
    width: 512
    height: 512
    enable_hr: true
    hr_scale: 2

profiles: # override from default profile(デフォルトプロファイルから上書き)
    xl:
        command:
            width: 1024
            height: 1024
            enable_hr: false
            refiner_switch_at: 0.7
    pory:
        load_profile: [xl]                                  # before Load profile xl(プロファイルxlを先に読み込む)      
        command:
            override_settings:                              # WebUIのSettingを上書きする
                CLIP_stop_at_last_layers: 2                 # CLIPの最終層を変更する(推奨 2)
                emphasis: "No norm"                         # 強調の設定
                override_settings_restore_afterwards: true  # 実行後にオプションを書き戻す
```

run profile(プロファイルを実行)
```
python cp2.py --profile xl input.yaml 
# width = 512, height = 512, enable_hr = true, hr_scale = 2

python cp2.py --profile xl input.yaml
# width = 1024, height = 1024, enable_hr = false, refiner_switch_at = 0.7
```
load_profile is profile load in profile(プロファイルから他のプロファイルを読み込む)
```yaml
    profile:
        xl:
            load_profile: [animal]
            command:
                width: 1024
                height: 1024
        animal:
            command:
                prompt: "animal"
                width: 512
                height: 512
```

This case is preload profile defaut next animal, last xl (この場合、デフォルトプロファイル -> animalを先に読み込みます)
load_profile is not suport nested profile(プロファイルは入れ子にできません)


### Parser(パーサー)
 sentence in \$\{ \} can be parsed (\$\{= \}の中に式が書けます)

Example(例)
```yaml
    seed: ${=random_int()} # random seed(ランダムシード)
    width: ${=int(${size}) * 2} # width = size * 2(幅 = サイズ * 2)

```

#### Parse tester (パーサーテスター)
```
> python tools.py parser_test '2 + x * y' 'x=3,y=4'
...
...
...
14.0

> python tools.py parser_test '"test" == str' 'str=test'
...
...
...
1       # true
```

#### current functions(現在の関数)
 not support boolean type (ブーリアン型はサポートされていません) retrun 0(false) or 1(true)(0(偽)または1(真)を返します)

functions(関数) str1,str2,.. are string(文字列) and x,y... are number(数値)
- chained("objects", 0.8, 3) : create chained string(連鎖変数) "object" = ${object} 0.8 is threshhold, 3 is count(0.8は閾値、3は回数)  
- choice("objects") : choice one sobjects(オブジェクトの中から1つ選択)
- contains(str1,str2, str3....) : str1 contains [str2, str3, ...] (文字列str1がstr2...を含むか)
- pow(x,y) : x^y(累乗)
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

# ComfyUI
- --api-comfy option is use ComfyUI API(ComfyUI APIを使う)
- Try to create workflow to run prompt in comfy(promptをcomfyで実行できるようにワークフローを作成を試みます)
- At present, only txt2img is supported, and hires.fix is not supported(現時点でサポートされているのはtxt2imgのみで、hires.fixはサポートされていません)
- You can also load workflow directly. Save the workflow for the API in ComfyUI(workflowを直接読み込むことも可能です。ComfyUIでAPI用のworkflowを保存してください)
- When you run the workflow directly, the behavior of the --api-comfy-save option is not guaranteed(Workflowを直接実行した場合、--api-comfy-saveオプションの挙動は保証されません)

## direct run workflow(ワークフローを直接実行)
```shell
python cp2.py --api-output-dir ./outputs/txt2img-images --api-comfy --api-base http://localhost:8188 --image-type webp --api-input-json ./workflow_api.json
```

## Use workflow instead of prompt(Promptの代わりにWorkflowを使う)
```yaml
version: 2
variables:
    seed: ${=random_int()}
    prompt: ['cat is run']
    negative: ['nsfw']
command: ./workflows_apijson
```

```json
{
  "3": {
    "inputs": {
      "seed": "${seed}",      // random seed(ランダムシード)
      "steps": 25,
      "cfg": 12.5,
      "sampler_name": "dpmpp_sde",
      "scheduler": "karras",
      "denoise": 1,
      "model": [
        "82",
        2
      ],
      "positive": [
        "82",
        0
      ],
      "negative": [
        "82",
        1
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "19": {   // positive prompt(ポジティブプロンプト)
    "inputs": {
      "width": 4096,
      "height": 4096,
      "crop_w": 0,
      "crop_h": 0,
      "target_width": 4096,
      "target_height": 4096,
      "text_g": "${prompt}",
      "text_l": "${prompt}",
      "clip": [
        "23",
        0
      ]
    },
    "class_type": "CLIPTextEncodeSDXL",
    "_meta": {
      "title": "positive prompt"
    }
  },
  "20": {   // negative prompt(ネガティブプロンプト)
    "inputs": {
      "width": 4096,
      "height": 4096,
      "crop_w": 0,
      "crop_h": 0,
      "target_width": 4096,
      "target_height": 4096,
      "text_g": "${prompt}",
      "text_l": "${prompt}",
      "clip": [
        "23",
        0
      ]
    },
    "class_type": "CLIPTextEncodeSDXL",
    "_meta": {
      "title": "negative prompt"
    }
  },
  // ...
  // Can save locally by setting the node id of "save_image_websocket_node" to "save_image_websocket_node"
  // Save image to websocket(画像をwebsocketに保存) の node idを"save_image_websocket_node"にするとローカルに保存可能
  "save_image_websocket_node": {  
    "inputs": {
      "images": [
        "8",        // node of "image"
        0
      ]
    },
    "class_type": "SaveImageWebsocket", 
    "_meta": {
      "title": "SaveImageWebsocket"
    }
  },
}
```

# issue(問題)
 - issue #1 nseted associative array is not supported(入れ子の連想配列はサポートされていません)
 - issue #2 DB query is not supported, yet (DBクエリーはまだサポートされていません)
 - issue #3 nested profile is not supported(入れ子プロファイルはサポートされていません)
 - issue #4 multi thread is not supported(マルチスレッドはサポートされていません)

# V1(旧バージョン)
 see [READMEV1.md](READMEV1.md)