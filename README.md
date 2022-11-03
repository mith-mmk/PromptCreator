# Prompt Creator
　I create automatic prompt creator for AUTOMATIC1111/stable-diffusion-webui.

- Beware of combination explosion
- Replace variable is \$\{n\} ex. \$\{1\},\$\{2\},...\$\{100}\
- If You use yaml mode,you can use \$\{name\} for variable (see below), but you cannot use reserved words ex. \$\{semicolon\}


```
usage: create_prompts.py [-h] [--append-dir APPEND_DIR] [--output OUTPUT] [--json [JSON]] [--api-mode [API_MODE]] [--api-base API_BASE]
                         [--api-output-dir API_OUTPUT_DIR]
                         input
```

  -h, --help            show this help message and exit

  --append-dir APPEND_DIR
                        direcory of input append prompt files

  --output OUTPUT       direcory of output file of prompt list file

  --json                output JSON

  --api-mode            output api force set --json
                        see https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API

  --api-base API_BASE  for call api from this script ex http://127.0.0.1:7860

  --api-output-dir API_OUTPUT_DIR
                        a directory of api output images 


# Setting
 Python 3.10+(Also 3.8 and above) and use there packages.
 
```
pip install pyyaml
pip install Pillow
pip install httpx
```

# Usage
## Text Mode
　Text mode is pre prompt for text file with list words file under append_dir.Replace order is \$\{1\},\$\{3\},\$\{3\}....,Files correspond in sorted order from 1 to n.If text mode must set --append-dir option. Prompt text's new lines are replace space.


ex:
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

## yaml mode
　A file extention is yaml or yml,Script is read yaml.

ex:
```
./create_promopts.py prompt.yml --output list.txt
```


ex: array mode
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

ex:variable mode

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

### mutiply mode
  Prompts is made by a round robin.


### random mode
 Prompts is made by random 

```yaml
version: 0.2  #Version is Not implement 
options:
#    filename: list.txt  #Not implement
    method: random # default= multiple,random, ...
    number: 200    # list limit, "multiple" is not use
    weight: True   # Weight mode = Ture or False, If False,script is note use weight
    default_weight: 0.1 # Default weight
append:
    - 0.2;blue      # weight 0.2
    - 0.3;yellow    # weight 0.3
    - white         # use default 0.1
```

### about recursive replace
 Replace order is yaml order.For this reason,a replace variable \$\{1\} uses \$\{2\}, \$\{3\} or after variables.

 ex.

```yaml
append:
    - # ${1}
        - ${2} eyes ${3} hair
    - # ${2}
        - 0.3;blue
        - 0.1;red
        - 0.6;
    - # ${3}
        - 0.5;blonde
        - 0.5;brown
```

for variable mode
```yaml
append:
    style:
        - ${eyecolor} eyes ${haircolor} hair
    eyecolor:
        - 0.3;blue
        - 0.1;red
        - 0.6;
    haircolor:
        - 0.5;blonde
        - 0.5;brown
```


### escape
If you want to use ;,you can instead of \\; or \$\{semicolon\}

### splitting replacement

Use \$\{name,num\}, num is replacement number(1..)

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

### filename mode
　Filename mode is replacement list reading from text file。Path is relative path of execution path.If # letter is comment.


```yaml
     append:
            - color.txt
```

ex:color.txt
```
# Color list
0.5;black
white
grey
red
blue
green
```

# issue
- img2img
- Overritde Prompt
- versioning