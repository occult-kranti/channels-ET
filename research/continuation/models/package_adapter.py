#!/usr/bin/env python3
"""Package the actual small pilot adapter, never the base-model weights."""
import hashlib,json,pathlib,zipfile
HERE=pathlib.Path(__file__).resolve().parent
def main():
 manifest=json.loads((HERE/'model-manifest.json').read_text());receipt=json.loads((HERE/'training-receipt.json').read_text());assert receipt['status']=='completed'
 source=pathlib.Path(receipt['adapterPath']);out=HERE/'adapter-export';out.mkdir(exist_ok=True)
 config=json.loads((source/'adapter_config.json').read_text());config['base_model_name_or_path']=manifest['model'];config['revision']=manifest['revision']
 (out/'adapter_config.json').write_text(json.dumps(config,indent=2)+'\n')
 (out/'adapter_model.safetensors').write_bytes((source/'adapter_model.safetensors').read_bytes())
 (out/'LICENSE.txt').write_bytes((pathlib.Path(manifest['cachePath'])/'LICENSE').read_bytes())
 (out/'README.md').write_text(f'''# Channeling digest CPU LoRA pilot\n\nThis is a 48-example, one-epoch feasibility adapter, not a validated expert model.\nBase model: {manifest['model']} at revision `{manifest['revision']}` (Apache-2.0).\nThe archive targets are pre-existing AI-generated Darryl Anka/Bashar-context question/answer-gist paraphrases. They are not transcript turns, verified speaker labels or factual ground truth.\n\nLoad the exact base with Transformers 4.51.3, then use PEFT 0.15.2 `PeftModel.from_pretrained(base, adapter_directory)`. CPU training used Torch 2.6.0+cpu, rank4, alpha8, q/v projection targets, sequence cap192,48 microsteps/12 optimizer steps. The bundle excludes all base-model weights and raw speech.\n\nDo not infer medical/scientific validity, speaker authenticity or extraterrestrial origin from a generated answer. Tiny-pilot lexical metrics do not establish general-domain quality. See the companion split, predictions and benchmark receipts.\n''')
 (out/'training-manifest.json').write_text(json.dumps({k:v for k,v in receipt.items() if k not in ['adapterPath','adapterFiles']},indent=2)+'\n')
 split=json.loads((HERE/'split.json').read_text())
 source_manifest={'sourceQaSha256':split['sourceQaSha256'],
                  'splitSha256':hashlib.sha256((HERE/'split.json').read_bytes()).hexdigest(),
                  'protocolSha256':hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
                  'sourceType':'Inherited AI-generated digest paraphrases, not original speech or human labels',
                  'train':[{'candidateId':r['id'],'sourcePath':r['sourcePath'],'sourceSha256':r['sourceSha256'],'sourcePointer':r['sourcePointer']} for r in split['train']]}
 (out/'training-source-manifest.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
 (out/'NOTICE.txt').write_text(f'''Pilot adapter release notice\n\nBase: {manifest['model']} at {manifest['revision']}, Apache-2.0. Full base weights are not included. The accompanying Apache-2.0 license applies to this experimental adapter distribution.\n\nTraining inputs are inherited AI-generated digest paraphrases from the user's MIT-licensed Bashar Index research data package. That MIT notice concerns the derived repository data/code; it does not transfer rights in original recordings, captions or performances. Training provenance and hashes appear in training-source-manifest.json. No raw speech or captions are included.\n\nThe adapter is a 48-example computational pilot. Its outputs have no human or physical-truth validation, and it is not an established state-of-the-art or source-grounded expert system.\n''')
 archive=HERE/'qwen-digest-lora-pilot.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.iterdir()):
   info=zipfile.ZipInfo(p.name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
 record={'status':'packaged_actual_adapter','archive':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
         'baseModel':manifest['model'],'baseRevision':manifest['revision'],'baseWeightsIncluded':False,'rawCaptionsIncluded':False,
         'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())]}
 (HERE/'adapter-package.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
