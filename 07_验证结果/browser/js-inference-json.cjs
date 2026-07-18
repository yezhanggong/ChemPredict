const fs = require('fs');
const vm = require('vm');

global.window = global;
vm.runInThisContext(fs.readFileSync(process.argv[2], 'utf8'), { filename: 'registries.js' });
vm.runInThisContext(fs.readFileSync(process.argv[3], 'utf8'), { filename: 'model_artifact.js' });
vm.runInThisContext(fs.readFileSync(process.argv[4], 'utf8'), { filename: 'model-v44.js' });
const candidate = global.ChemPredictModel.virtualCandidates().find((row) => row.id === process.argv[5]);
if (!candidate) throw new Error(`Unknown candidate ${process.argv[5]}`);
const result = global.ChemPredictModel.predictCustom({
  systemId: 'nhp_deoxygenative_asymmetric_cyanation',
  precursorType: 'secondary_benzylic_nhp_ether',
  radicalClass: 'carbon_aryl_benzylic',
  reactionFamily: 'nhp_ether_deoxygenative_asymmetric_cyanation',
  conditionChanges: [],
  scopeGroup: String(candidate.scope_group).startsWith('alkyl') ? 'alkyl_series' : candidate.scope_group,
  features: candidate,
});
process.stdout.write(JSON.stringify(result));
