'use strict';
const publisherAudioState={data:null,error:null};
async function loadPublisherAudio(audit){
  const ref=audit.publisher_audio_acquisition;if(!ref)return;
  try{
    if(ref.file!=='acquisition.json')throw Error('Unexpected publisher-audio receipt path.');
    const response=await fetch(ref.file);if(!response.ok)throw Error('Audio receipts returned HTTP '+response.status);
    const d=await response.json();
    if(d.schema_version!==1||!Array.isArray(d.records)||d.synthetic_fixture_run===true)throw Error('Invalid publisher-audio receipts.');
    publisherAudioState.data=d;publisherAudioState.error=null;
  }catch(e){publisherAudioState.data=null;publisherAudioState.error=e.message;}
}
function publisherAudioView(){
  const d=publisherAudioState.data;
  if(!d)return publisherAudioState.error?`<section id="publisher-audio-acquisition" class="section"><h2>Publisher-audio receipts unavailable</h2><p class="empty">${esc(publisherAudioState.error)}</p><p><a href="acquisition.json">Open the receipt file</a></p></section>`:'';
  const s=d.summary||{},f=d.frame||{},held=arr(d.records).filter(r=>r.recognition_hold_active===true);
  return `<section id="publisher-audio-acquisition" class="section" tabindex="-1">
    <span class="eyebrow">RETAINED AUDIO · SEPARATE TEXT STATES</span>
    <div class="section-head"><h2>From retained audio to usable text.</h2><p>Receipt snapshot: ${esc(d.generated_at)} · ${esc(human(d.status))}. This saved publisher-source frame is separate from YouTube uploads and the historical text studies.</p></div>
    <div class="discovery-strip audio-retention-metrics"><div><b>${number(s.completed_publications)}</b><span>retained publisher publications</span></div><div><b>${number(f.total_entries)}</b><span>finite discovery-frame entries</span></div><div><b>${finite(s.retained_bytes)?(s.retained_bytes/1e6).toLocaleString('en',{maximumFractionDigits:1}):'Unknown'}</b><span>MB of retained audio</span></div><div><b>${finite(s.decoded_duration_seconds)?(s.decoded_duration_seconds/3600).toLocaleString('en',{maximumFractionDigits:2}):'Unknown'}</b><span>decoded audio hours</span></div></div>
    <div class="discovery-strip audio-text-metrics" aria-label="Current text processing states"><div><b>${number(s.local_asr_completed)}</b><span>completed local ASR editions</span></div><div><b>${number(s.publisher_caption_linked)}</b><span>publisher-caption linked recordings</span></div><div><b>${number(s.recognition_holds)}</b><span>recognition holds · text unadmitted</span></div><div><b>${number(s.pending_local_asr)}</b><span>pending local ASR</span></div></div>
    <div class="scope-note"><p><strong>A complete finite audio frame is not a complete transcript corpus.</strong> Channel upload totals and all historical publisher episodes remain unknown. Retained files are full-duration lossy Opus derivatives held in the workspace, with acquisition hashes in the receipts.</p><p>${number(s.normalization_repaired)} accepted ASR editions have timestamp-display repairs; those repairs do not verify recognition accuracy. Caption alignment and accuracy are unverified. The ${number(s.publisher_written_message_linked)} linked written messages overlap other text states and are not additional recordings. New acquisition counts do not change earlier frozen analysis denominators.</p></div>
    <div class="table-wrap" role="region" tabindex="0" aria-label="Publisher audio storage and transcription distribution"><table class="source-table"><thead><tr><th>Publisher / account</th><th>Retained</th><th>Caption linked</th><th>Local ASR</th><th>Recognition holds</th><th>Pending ASR</th></tr></thead><tbody>${arr(d.channels).map(c=>{const m=c.related_publisher_material||{};return `<tr><th scope="row">${esc(c.id)}</th><td>${number(m.current_new_audio_sources_retained)}</td><td>${number(m.current_new_audio_caption_linked)}</td><td>${number(m.current_new_audio_local_asr)}</td><td>${number(m.current_new_audio_recognition_holds)}</td><td>${number(m.current_new_audio_asr_pending)}</td></tr>`;}).join('')}</tbody></table></div>
    ${held.length?`<div class="audio-holds"><h3>Recognition holds need review.</h3>${held.map(r=>`<article class="inspection-note"><p><strong>${link(r.source_url,r.title)}</strong></p><p>${esc(r.publisher_handle)} · ${esc(r.publication_id)}</p><p>Held after recognition failure: ${esc(arr(r.asr_failed_editions).map(x=>human(x.reason_code)).join('; ')||'See receipt diagnostics')}. Audio remains retained; this attempt has no admitted transcript or analysis result.</p></article>`).join('')}</div>`:'<p class="table-note">No active recognition holds in this receipt snapshot.</p>'}
    <div class="download-list"><a href="../channeling-network/#coverage">Filter all retained recordings and export metadata</a><a href="acquisition.json" download>Download complete acquisition receipts</a><a href="../channeling-network/#analysis">Open separately dated transcript analyses</a></div>
  </section>`;
}
