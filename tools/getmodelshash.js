const path = require('path');
const crypto = require('crypto');
const fs = require('fs');

/*
  use nodejs 14.15.4 or later
  usage:
  node ./getmodelshash.js <hostname|filename|directory>? <outputJson>? <exportHashJson>? <importHashJson>? <sort>?
    <hostname|filename|directory>: hostname or filename or directory (default: http://localhost:7860)
    <outputJson>: output json filename (default: outputs/models.json)
    <exportHashJson>: export hash json filename (default: outputs/hash.json)
    <importHashJson>: import hash json filename (default: f:/twitter/hash.json)
    <sort>: sort hash json filename (default: false)
*/


function writeJsonSync(json, filename) {
    try {
        if(filename != null) {
            const fd = fs.openSync(filename,'w');
            fs.writeSync(fd,JSON.stringify(json,null,2),0);
            fs.closeSync(fd);    
        } else {
            console.log('filename is null');
        }
    } catch(e) {
        console.log(`Write error ${filename} ${e}`);
    }
}

function writeArrayToJson(array, filename) {
    try {
        if(filename != null) {
            let str = '{\n';
            const lines = array.map(v => `  "${v.hash}": "${v.modelName}"`);
            str += lines.join(',\n');
            str += '\n}\n';
            console.log(str);
            const fd = fs.openSync(filename,'w');
            fs.writeSync(fd, str);
            fs.closeSync(fd);    
        } else {
            console.log('filename is null');
        }
    } catch(e) {
        console.log(`Write error ${filename} ${e}`);
    }
}

async function createHashFromModelName(modelName) {
    await fetch(url + '/sdapi/v1/load-checkpoints');
}

function createHashFromFiles(files) {
    const hashList = {};
    const promises = [];
    files.forEach(file => {
        const promise = calc_hash(file);
        promises.push(promise); 
        function calc_hash(file)  {
            return new Promise((resolve, reject) => {
                const hash = crypto.createHash('sha256');
                const filesize = fs.statSync(file).size;
                let readed = 0;
                try {
                    const stream = fs.createReadStream(file, {highWaterMark: 1024 * 1024});
                    stream.on('data', (data) => {
                        readed += data.length;
                        const progress = Math.floor(readed / filesize * 1000) /10;
                        const progressStr = `${progress}`.padStart(5);
                        process.stdout.write(`${path.basename(file)} ${progressStr} % ${readed} bytes / ${filesize} bytes\n`);
                        // 1行戻る
                        process.stdout.write('\u001b[1A');
                        // dulation
                        hash.update(data);
                    });
                    stream.on('end', () => {
                        console.log('end');
                        const filebase = path.basename(file);
                        const hash8 = hash.digest('hex').slice(0,10);
                        const json = {};
                        json[hash8] = filebase;
                        resolve(json);
                    });
                } catch (err) {
                    reject(err);
                }
            });
        }
    });
    Promise.all(promises).then((results) => {
        results.forEach((result) => {
            console.log(result);
            hashList[result.hash] = result.filename;
        });
    }).catch((err) => {
        console.log(err);
    });
    return hashList;
}



function getModlesHashFromAutomatic1111(url,outputJson,exportHashJson=null,importHashJson=null,sort=false) {
    const hashList = (importHashJson != null && fs.existsSync(importHashJson)) ? require(importHashJson) : {};

    fetch(url + '/sdapi/v1/refresh-checkpoints', {method: 'POST'})
    .then((reults) => {
        fetch(url + '/sdapi/v1/sd-models')
        .then(response => response.json())
        .then(json => {
            writeJsonSync(json, outputJson);
            json.forEach(row => {
                if (row.hash != null && hashList[row.hash] == null) hashList[row.hash] = row.model_name;
            });
            if (!sort) {
                writeJsonSync(hashList, exportHashJson);
                return
            }

            const sorter = [];
            for (const [key, value] of Object.entries(hashList)) {
                sorter.push({hash: key,modelName: value});
            }
            sorter.sort((a,b) => { 
                const aName = a.modelName.toLowerCase();
                const bName = b.modelName.toLowerCase();
                if (aName > bName) {
                    return 1;
                } else if (aName < bName) {
                    return -1;
                } else {
                    return 0;
                }
            });
            writeArrayToJson(sorter, exportHashJson);
        })
        .catch(err => {
            console.log(err)
        });
    }).catch(err => {
        console.log(err)
    });
}

// node getmodelshash.js <hostname|filename|directory>? <outputJson>? <exportHashJson>? <importHashJson>? <sort>?

const args = process.argv.slice(2);
let url = args[0] || 'http://localhost:7860';
const outputJson = args[1] || 'outputs/models.json';
const exportHashJson = args[2] || 'outputs/hash.json';
const importHashJson = args[3] || 'outputs/hash.json';
const sort = args[4] == 'sort' ? true : false;


if (/^https?:\/\//.test(url)) {
    // last / is not required
    if (url.endsWith('/')) url = url.slice(0, -1);
    getModlesHashFromAutomatic1111(url, outputJson, exportHashJson, importHashJson, sort);
    return;
} else {
    // file
    const path = url
    const prevhashList = (importHashJson != null && fs.existsSync(importHashJson)) ? require(importHashJson) : {};
    if (fs.existsSync(path)) {
        // filr or directory
        let files = [];
        if (fs.statSync(path).isDirectory()) {
            // glob files
            files = fs.readdirSync(path).map(file => path + '/' + file);
        } else {
            files = [path];
        }
        const hashList = createHashFromFiles(files);
    } else {
        console.log(`file not found ${path}`);
    }
    // export hash.json
    console.log(`export ${exportHashJson}`);
}

