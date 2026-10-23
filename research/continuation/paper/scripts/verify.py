#!/usr/bin/env python3
"""Compile the standalone manuscript package and inspect actual render outputs."""
import hashlib,json,os,pathlib,subprocess,tempfile,zipfile
P=pathlib.Path(__file__).resolve().parents[1];work=pathlib.Path(tempfile.mkdtemp(prefix='channels-et-paper-clean-',dir='/workspace'))
with zipfile.ZipFile(P/'channels-et-source.zip') as archive:archive.extractall(work)
env=dict(os.environ,TEXMFHOME='/workspace/channels-et-tex/texmf',TEXMFVAR='/workspace/channels-et-tex/var',TEXMFCONFIG='/workspace/channels-et-tex/config',SOURCE_DATE_EPOCH='1792713600',FORCE_SOURCE_DATE='1')
commands=[['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['bibtex','main'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex']]
for index,command in enumerate(commands):
 result=subprocess.run(command,cwd=work,env=env,capture_output=True,text=True);(work/f'pass-{index}.log').write_text(result.stdout+result.stderr);result.check_returncode()
pdf=P/'channels-et-paper.pdf'
original_text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'])
clean_text=subprocess.check_output(['pdftotext','-layout',str(work/'main.pdf'),'-'])
assert original_text==clean_text,'Clean package changes extracted manuscript page text'
log=(P/'build/pass3.log').read_text();assert 'Overfull' not in log,'Overfull boxes remain';assert 'undefined' not in log.lower(),'Undefined references/citations remain'
font_report=subprocess.check_output(['pdffonts',str(pdf)],text=True)
assert 'Type 3' not in font_report,'Type 3 font in manuscript/figure'
font_rows=font_report.splitlines()[2:]
assert font_rows and all(row.split()[-5]=='yes' for row in font_rows),'Font embedding not established'
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);pages=int(next(x.split(':')[1] for x in info.splitlines() if x.startswith('Pages:')))
render=work/'render';render.mkdir();subprocess.run(['pdftoppm','-png','-scale-to','1200',str(pdf),str(render/'page')],check=True,capture_output=True)
assert len(list(render.glob('page-*.png')))==pages
receipt={'status':'PASS','pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'source_zip_sha256':hashlib.sha256((P/'channels-et-source.zip').read_bytes()).hexdigest(),'pages':pages,'clean_package':{'directory':str(work),'commands':commands,'all_exit_zero':True,'extracted_page_text_identical':True},'fonts':{'no_type3':True,'report':font_report},'latex':{'overfull_boxes':0,'undefined_citations_or_references':0},'render':{'directory':str(render),'pages_rendered':pages,'visual_inspection':'Pending inspection of this exact candidate; rendering alone does not establish readability.'},'scope':'Local build and artifact checks; no human peer review or venue-compliance certification.'}
(P/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
