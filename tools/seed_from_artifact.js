// One-time seed: the phase-one hand-entered data objects from the "Which Model Today"
// artifact (Sept 7, 2026), dumped to data/2026-09-07.json so the first automated
// rebuild has a baseline to diff against. Not part of the daily pipeline.
const ACCESS = {
  'Claude Fable 5.1':'claude','Claude Fable 5':'claude','Claude Opus 5':'claude',
  'GPT-6 Astra':'chatgpt','GPT-5.6 Sol':'chatgpt','GPT-5.6 Terra':'chatgpt','GPT-5.6 Luna':'chatgpt',
  'Grok 4.6':'grok'
};
const B = {
  terminal:{ name:'Terminal-Bench v2.1', kind:'task', src:'Artificial Analysis', d:{'Claude Fable 5.1':91,'Claude Opus 5':89,'Grok 4.6':88,'GPT-6 Astra':88,'GPT-5.6 Terra':88,'GPT-5.6 Sol':88,'Gemini 3.8 Flash':88,'Muse Spark 1.3':86,'Kimi K3':85,'Claude Fable 5':85,'GLM-5.3-Flash':84,'GLM-5.3':84,'Qwen3.8 2.4T A95B':82,'GPT-5.6 Luna':81,'Qwen3.8 278':80,'DeepSeek V4 Pro 0813':79,'MiniMax-M3':65,'Inkling':55}},
  scicode:{ name:'SciCode', kind:'task', src:'Artificial Analysis', d:{'Claude Fable 5.1':62,'Claude Fable 5':60,'Kimi K3':59,'Muse Spark 1.3':57,'GLM-5.3':56,'GPT-5.6 Sol':56,'Claude Opus 5':56,'GPT-6 Astra':54,'GPT-5.6 Terra':54,'Gemini 3.8 Flash':54,'Grok 4.6':54,'GPT-5.6 Luna':53,'Qwen3.8 2.4T A95B':52,'DeepSeek V4 Pro 0813':49,'Inkling':46,'GLM-5.3-Flash':46,'MiniMax-M3':45,'Qwen3.8 278':45}},
  gdpval:{ name:'GDPval-AA v2', kind:'task', src:'Artificial Analysis', d:{'Claude Fable 5.1':68,'Claude Opus 5':68,'GLM-5.3-Flash':63,'GLM-5.3':63,'Muse Spark 1.3':63,'Grok 4.6':61,'Claude Fable 5':61,'Qwen3.8 2.4T A95B':61,'GPT-5.6 Sol':61,'Kimi K3':58,'GPT-6 Astra':56,'DeepSeek V4 Pro 0813':54,'GPT-5.6 Luna':53,'GPT-5.6 Terra':53,'Gemini 3.8 Flash':52,'Qwen3.8 278':52,'MiniMax-M3':44,'Inkling':37}},
  tau:{ name:'τ³-Banking', kind:'task', src:'Artificial Analysis', d:{'Muse Spark 1.3':52,'Grok 4.6':51,'GLM-5.3':50,'Qwen3.8 2.4T A95B':49,'Qwen3.8 278':48,'GLM-5.3-Flash':47,'Claude Fable 5.1':47,'Kimi K3':46,'Gemini 3.8 Flash':45,'GPT-5.6 Sol':44,'Claude Opus 5':42,'GPT-6 Astra':41,'GPT-5.6 Terra':40,'DeepSeek V4 Pro 0813':40,'Claude Fable 5':38,'GPT-5.6 Luna':31,'Inkling':29,'MiniMax-M3':15}},
  lcr:{ name:'AA-LCR', kind:'task', src:'Artificial Analysis', d:{'Kimi K3':83,'Gemini 3.8 Flash':81,'MiniMax-M3':80,'Claude Fable 5.1':80,'GPT-5.6 Terra':80,'Muse Spark 1.3':79,'GPT-5.6 Luna':78,'GLM-5.3-Flash':78,'GPT-5.6 Sol':78,'Qwen3.8 278':77,'Claude Fable 5':77,'GLM-5.3':76,'Claude Opus 5':76,'DeepSeek V4 Pro 0813':75,'Qwen3.8 2.4T A95B':75,'Grok 4.6':75,'GPT-6 Astra':74,'Inkling':73}},
  omni:{ name:'AA-Omniscience Accuracy', kind:'task', src:'Artificial Analysis', d:{'Claude Fable 5.1':67,'Claude Fable 5':65,'GPT-6 Astra':63,'Claude Opus 5':61,'GPT-5.6 Sol':59,'Gemini 3.8 Flash':55,'DeepSeek V4 Pro 0813':49,'Grok 4.6':48,'Kimi K3':48,'GPT-5.6 Terra':47,'Muse Spark 1.3':44,'GPT-5.6 Luna':43,'Inkling':42,'GLM-5.3':34,'Qwen3.8 2.4T A95B':31,'GLM-5.3-Flash':28,'MiniMax-M3':17,'Qwen3.8 278':16}},
  nohalluc:{ name:'Non-hallucination rate', kind:'task', src:'Artificial Analysis', d:{'MiniMax-M3':82,'GLM-5.3-Flash':72,'GLM-5.3':70,'Qwen3.8 278':70,'Muse Spark 1.3':66,'Grok 4.6':66,'Qwen3.8 2.4T A95B':61,'GPT-6 Astra':49,'Kimi K3':47,'Gemini 3.8 Flash':45,'Claude Opus 5':39,'Claude Fable 5':36,'Inkling':32,'Claude Fable 5.1':27,'GPT-5.6 Terra':12,'GPT-5.6 Sol':8,'GPT-5.6 Luna':7,'DeepSeek V4 Pro 0813':5}},
  gdppdf:{ name:'GDP.pdf (all criteria met)', kind:'task', src:'Artificial Analysis, Sept 4 (Benchmark Scout PR 1, verified)', d:{'GPT-6 Astra':33.2,'GPT-5.6 Sol':28.2,'Claude Fable 5.1':26.2}},
  webdev:{ name:'Arena WebDev', kind:'votes', src:'arena.ai, Sept 5 (verified)', elo:true, d:{'GPT-6 Astra':1797,'Claude Fable 5.1':1762,'Claude Opus 5':1688,'Qwen3.8 Max':1686,'Kimi K3':1674,'Grok 4.6':1625,'Gemini 3.6 Flash':1604,'GPT-5.6 Sol':1588}},
  text:{ name:'Arena Text', kind:'votes', src:'arena.ai, Sept 2', elo:true, d:{'Claude Fable 5':1507,'Claude Fable 5.1':1504,'Muse Spark 1.2':1499,'Gemini 3.8 Flash':1494,'Claude Opus 5':1493,'Kimi K3':1489,'GPT-5.6 Sol':1483,'GLM-5.3':1482}},
  image:{ name:'AA Image Arena', kind:'votes', src:'Artificial Analysis, Sept 6', elo:true, d:{'GPT Image 2':1178,'MAI-Image-2.6':1149,'Reve 2.1':1127,'Nano Banana 2':1121,'Muse Image':1116,'GPT Image 1.5':1114,'MAI-Image-2.5':1112,'Nano Banana Pro':1099,'Qwen-Image-3.0-Pro':1086,'Seedream 5.0 Pro':1083,'Grok Imagine':1034}},
  video:{ name:'AA Video Arena (with audio)', kind:'votes', src:'Artificial Analysis, Sept 6', elo:true, d:{'Wan 3.0':1238,'Gemini Omni Flash':1238,'MiniMax H3':1228,'Seedance 2.0':1222,'Kling 3.0 Pro':1108,'Veo 3.1':1091,'Grok Imagine Video':1062}}
};
const MEDIA_ACCESS = {'GPT Image 2':'chatgpt','GPT Image 1.5':'chatgpt','Grok Imagine':'grok','Grok Imagine Video':'grok'};
const SECOND = [
 {title:'Vals Index', unit:'%', max:70,
  meta:'Vals AI, Sept 5. A GDP-weighted blend across finance, coding and legal work. 55 models tested.',
  note:'Agrees with Artificial Analysis on the top of the board: Fable 5.1 first, Astra third.',
  d:[['Claude Fable 5.1',68.83],['Claude Opus 5',67.21],['GPT-6 Astra',66.61],['Claude Fable 5',66.04]]},
 {title:'Terminal-Bench 2.1, second run', unit:'%', max:90,
  meta:'Vals AI, Sept 5. Terminus 2 harness, pass@1.',
  note:'This is the disagreement. Artificial Analysis has Fable 5.1 first on the same named test at 91 with Astra at 88. Vals has Astra first. Same test, different harness, opposite answer.',
  d:[['GPT-6 Astra',87.27],['GPT-5.6 Sol',85.77],['Claude Fable 5.1',85.02],['Claude Opus 5',84.64]]},
 {title:'Code Migration', unit:'%', max:70,
  meta:'Vals AI, Sept 5. Rebuild a working program in another language; scored on hidden behavior tests.',
  note:'Astra leads by ten points, but Vals notes even its ports pass only about two thirds of the hidden tests. Automated migration is not turnkey.',
  d:[['GPT-6 Astra',67.7],['Claude Opus 5',57.5]]},
 {title:'Epoch Capabilities Index', unit:'', max:175,
  meta:'Epoch AI, Sept 5. A single capability score across 267 models.',
  note:'Astra ranks 1 of 267 at 169 (90% confidence 165 to 174). Fable 5.1 ranks 3 at 163 (160 to 166). The intervals nearly touch, so read this as a narrow lead, not a gulf.',
  d:[['GPT-6 Astra',169],['Claude Fable 5.1',163]]},
 {title:'Agent Arena, overall', unit:'%', max:18,
  meta:'arena.ai, Sept 5. Blind human votes on agent work; the figure is net improvement over the baseline.',
  note:'The first head-to-head human board for agent tasks. Fable 5.1 at maximum effort ranks first, 15.87% plus or minus 2.84% over 6,796 sessions. This supports the supervising-agents pick.',
  d:[['Claude Fable 5.1 (Max)',15.87],['Hy4 preview (open, rank 2)',8.48]]}
];
const NEWS=[
 {tag:'Policy · Sept 5', title:'Seattle Times and Newsday sue OpenAI and Microsoft',
  body:'The Seattle Times and Newsday filed a copyright lawsuit in the Southern District of New York against OpenAI and Microsoft. The suit alleges scraping of paywalled journalism for AI training and related claims.',
  why:'Two more newsrooms are seeking court limits on how OpenAI and Microsoft use paywalled reporting in training and products.',
  links:[['Court filing','https://storage.courtlistener.com/recap/gov.uscourts.nysd.672142/gov.uscourts.nysd.672142.1.0.pdf','primary'],['TechCrunch','https://techcrunch.com/2026/09/05/seattle-times-and-newsday-are-the-latest-publications-to-sue-openai-and-microsoft/','independent']]},
 {tag:'Policy · Sept 6', title:'Authors contest claims on Anthropic settlement payouts',
  body:'Authors in Anthropic\'s $1.5 billion copyright settlement say publishers and some literary agents are filing claim shares that conflict with the settlement\'s 50-50 split or rights-reversion rules. The settlement pays about $3,000 per pirated work under those allocation rules.',
  why:'Authors deciding whether to dispute payment allocations face conflicting claims that can cut what they receive from the settlement.',
  links:[['TechCrunch','https://techcrunch.com/2026/09/06/authors-push-back-as-publishers-and-agents-seek-share-of-anthropic-settlement/','independent']]},
 {tag:'Releases · Sept 6', title:'Meta ships Muse Voice Transcribe for live speech',
  body:'Meta Superintelligence Labs released Muse Voice Transcribe, a real-time speech transcription model with speaker diarization and adaptive delay. It is available now in Meta AI and through the Meta Model API at $0.18 per hour. Only Meta has published performance figures for the speaker-separation work.',
  why:'Developers and Meta AI users can buy live transcription with speaker labels at a listed API price today.',
  links:[['Meta research post','https://research.meta.ai/blog/introducing-muse-voice-transcribe','vendor'],['The Decoder','https://the-decoder.com/metas-new-real-time-audio-model-is-the-foundation-for-ai-assistants-that-never-stop-listening/','vendor writeup']]}
];
const EFF=[
 ['Claude Fable 5.1','max with fallback',57,6.12,70,264.9,'claude'],
 ['GPT-6 Astra','max',55,2.57,71,384.3,'chatgpt'],
 ['GPT-6 Astra','xhigh',54,1.85,67,160.4,'chatgpt'],
 ['Claude Opus 5','max',54,4.21,58,62.1,'claude'],
 ['Claude Fable 5.1','xhigh with fallback',54,null,67,109.5,'claude','*'],
 ['Claude Opus 5','xhigh',53,3.36,54,34.4,'claude'],
 ['GPT-6 Astra','high',53,1.41,64,95.0,'chatgpt'],
 ['Claude Fable 5','with fallback',53,5.62,68,103.6,'claude'],
 ['Muse Spark 1.3','max',53,0.96,190,18.7,null],
 ['GPT-6 Astra','medium',52,1.16,61,9.7,'chatgpt'],
 ['Claude Opus 5','high',52,2.44,54,18.4,'claude'],
 ['Claude Fable 5.1','high with fallback',52,null,56,25.7,'claude','*'],
 ['GPT-5.6 Sol','max',51,1.25,85,163.0,'chatgpt'],
 ['Grok 4.6','high',51,1.25,63,52.0,'grok'],
 ['Claude Fable 5.1','medium with fallback',50,null,56,17.2,'claude','*'],
 ['GPT-5.6 Sol','xhigh',50,0.89,82,64.0,'chatgpt'],
 ['Claude Opus 5','medium',50,1.36,53,4.7,'claude'],
 ['Grok 4.6','xhigh',49,null,64,58.2,'grok','*'],
 ['GPT-6 Astra','low',49,0.63,61,2.5,'chatgpt'],
 ['Grok 4.6','medium',48,null,63,41.9,'grok','*'],
 ['GPT-5.6 Sol','high',48,0.61,73,17.9,'chatgpt'],
 ['Claude Fable 5.1','low with fallback',48,null,55,6.5,'claude','*'],
 ['Gemini 3.8 Flash','high',47,0.74,334,10.8,null],
 ['GPT-5.6 Terra','max',47,0.81,115,168.8,'chatgpt'],
 ['GPT-5.6 Sol','medium',46,0.37,72,6.4,'chatgpt'],
 ['Claude Opus 5','low',44,0.64,53,2.3,'claude'],
 ['GPT-5.6 Luna','max',43,0.10,129,150.5,'chatgpt'],
 ['Grok 4.6','low',42,null,57,6.8,'grok','*'],
 ['GPT-5.6 Sol','low',41,0.23,74,3.3,'chatgpt']
];

const bench = {};
for (const [k, b] of Object.entries(B)) {
  bench[k] = { name: b.name, kind: b.kind, src: b.src, elo: !!b.elo,
    fetched: b.kind === 'votes' ? (k==='webdev'||k==='text' ? '2026-09-05' : '2026-09-06') : '2026-09-03',
    index_version: null, stale: false, d: b.d };
}
const eff = EFF.map(r => ({ model: r[0], effort: r[1], score: r[2], cost_per_task: r[3], speed: r[4], wait_s: r[5], access: r[6] || null, estimate: r[7] === '*' }));
const out = {
  schema: 1, date: '2026-09-07', built_at: '2026-09-07T03:00:00Z', built_by: 'hand (phase one artifact, seeded by tools/seed_from_artifact.js)',
  status: 'ok', status_notes: [],
  access: ACCESS, media_access: MEDIA_ACCESS,
  bench, second: SECOND, news: NEWS,
  news_meta: { editor_file: 'inbox/news/2026-09-07-edited.md', considered: 4, note: 'Chosen by the Editor agent from 4 items filed by the News Scout, which is far below its 20 to 40 target, so this is a thin choice set rather than a real selection.' },
  eff: { index: 'Artificial Analysis Intelligence Index v4.2', fetched: '2026-09-06', rows: eff },
  picks: {}, changes: [], health: [], pending_prs: []
};
require('fs').writeFileSync(process.argv[2], JSON.stringify(out, null, 1));
console.log('wrote', process.argv[2]);
