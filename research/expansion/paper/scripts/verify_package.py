#!/usr/bin/env python3
"""Compile the delivered package in isolation and compare actual page text."""
import hashlib,json,os,pathlib,subprocess,tempfile,zipfile

root=pathlib.Path(__file__).resolve().parents[1]
work=pathlib.Path(tempfile.mkdtemp(prefix='expansion-paper-clean-',dir='/workspace'))
with zipfile.ZipFile(root/'channeling-atlas-expansion-source.zip') as z:
    z.extractall(work)
commands=[['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['bibtex','main'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex']]
for index,cmd in enumerate(commands):
    result=subprocess.run(cmd,cwd=work,capture_output=True,text=True,env=dict(os.environ,SOURCE_DATE_EPOCH='1792713600',FORCE_SOURCE_DATE='1'))
    (work/f'check-{index}.log').write_text(result.stdout+result.stderr)
    result.check_returncode()
pdf=root/'channeling-atlas-expansion-paper.pdf'
text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'])
clean_text=subprocess.check_output(['pdftotext','-layout',str(work/'main.pdf'),'-'])
assert text==clean_text,'Clean package changed the manuscript page text'
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
pages=int(next(line.split(':')[1] for line in info.splitlines() if line.startswith('Pages:')))
final_log=(root/'build/pass3.log').read_text()
assert 'Overfull' not in final_log,'Overfull TeX boxes remain'
assert 'undefined' not in final_log.lower(),'Undefined references/citations remain'
render=work/'render';render.mkdir()
subprocess.run(['pdftoppm','-png','-scale-to','1100',str(pdf),str(render/'page')],check=True,capture_output=True)
assert len(list(render.glob('page-*.png')))==pages
receipt={'status':'PASS','pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'source_zip_sha256':hashlib.sha256((root/'channeling-atlas-expansion-source.zip').read_bytes()).hexdigest(),'pages':pages,'clean_package_compile':{'path':str(work),'commands':commands,'all_exit_zero':True,'extracted_page_text_identical':True},'render':{'pages_rendered':pages,'directory':str(render),'all_pages_rendered':True,'visual_inspection':'Pending inspection of this exact artifact; rendering alone does not establish readability.'},'latex':{'overfull_boxes':0,'undefined_references_or_citations':0},'limitations':['No human review, transcript accuracy audit, or successful new YouTube retrieval.','PDF byte equality is not required because compilation timestamps may change; extracted page text is compared exactly.']}
(root/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
