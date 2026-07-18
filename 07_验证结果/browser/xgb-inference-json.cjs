const fs = require('fs');
const vm = require('vm');

global.window = global;
global.CHEMPREDICT_ARTIFACT = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
vm.runInThisContext(fs.readFileSync(process.argv[3], 'utf8'), { filename: 'registries.js' });
vm.runInThisContext(fs.readFileSync(process.argv[4], 'utf8'), { filename: 'model-v44.js' });
const target = process.argv[5];
const record = global.CHEMPREDICT_ARTIFACT.known_scope.find((row) => row.id === process.argv[6]);
if (!record) throw new Error(`Unknown scope id ${process.argv[6]}`);
record.hammett_sigma_mp_x_para_sub_count = Number(record.hammett_sigma_mp) * Number(record.para_sub_count);
const prediction = global.ChemPredictModel.modelPrediction(global.CHEMPREDICT_ARTIFACT.models[target], record);
process.stdout.write(JSON.stringify({ prediction }));
