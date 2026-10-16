// Execute the actual inline explorer script against a small DOM harness.
// This checks data/control wiring and arithmetic; it is not a browser render.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const root=require('path').resolve(__dirname,'..');
const html=fs.readFileSync(root+'/docs/index.html','utf8');
class Element{
 constructor(tag='div'){this.tag=tag;this.attributes={};this.children=[];this.style={};this.listeners={};this.value='';this.hidden=false;this._text='';}
 set textContent(v){this._text=String(v);this.children=[];}
 get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
 setAttribute(k,v){this.attributes[k]=String(v);}
 getAttribute(k){return this.attributes[k];}
 append(...nodes){this.children.push(...nodes);}
 appendChild(n){this.children.push(n);return n;}
 replaceChildren(...nodes){this._text='';this.children=[...nodes];}
 addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
 fire(type,opts={}){for(const fn of this.listeners[type]??[])fn({preventDefault(){},...opts});}
 focus(){this.focused=true;}
}
const elements={};
for(const match of html.matchAll(/<([a-z0-9-]+)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)){
 const [,tag,attrs,id]=match;assert(!elements[id],`Duplicate id ${id}`);const el=new Element(tag);elements[id]=el;
 for(const a of attrs.matchAll(/([\w-]+)="([^"]*)"/g))el.setAttribute(a[1],a[2]);
 el.value=el.attributes.value??'';el.hidden=/\bhidden\b/.test(attrs);
}
for(const match of html.matchAll(/<select\b[^>]*id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g))elements[match[1]].value=match[2].match(/<option\s+value="([^"]+)"/)[1];
const embedded=html.match(/<script type="application\/json" id="study-evidence">([\s\S]*?)<\/script>/)[1];elements['study-evidence'].textContent=embedded;
const script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const document={getElementById(id){assert(elements[id],`Missing DOM id ${id}`);return elements[id];},createElement(tag){return new Element(tag);}};
vm.runInNewContext(script,{document,console},{timeout:2000});
const text=id=>elements[id].textContent;
const set=(id,value,event='change')=>{elements[id].value=String(value);elements[id].fire(event);};
const checks=[];
function check(name,fn){fn();checks.push({name,passed:true});}
check('Embedded aggregate JSON equals the two source reports',()=>{
 const e=JSON.parse(embedded);for(const name of ['pricing','reserve']){
  const raw=fs.readFileSync(root+`/reports/${name}_final.json`);assert.deepStrictEqual(e[name],JSON.parse(raw));assert.strictEqual(e.source_sha256[`${name}_final.json`],crypto.createHash('sha256').update(raw).digest('hex'));
 }
});
check('Default premium identity: loss 100 / (1 - .25 - .05)',()=>assert.strictEqual(text('premium-index'),'142.9'));
check('Zero loading identity',()=>{set('expense',0,'input');set('margin',0,'input');assert.strictEqual(text('premium-index'),'100.0');});
check('Upper slider bounds remain finite and reconcile to 325',()=>{set('inflation',30,'input');set('expense',40,'input');set('margin',20,'input');assert.strictEqual(text('premium-index'),'325.0');assert.strictEqual(Number(text('loss-index'))+Number(text('expense-index'))+Number(text('margin-index')),325);});
check('Intermediate assumption scenario and fixed study score',()=>{set('inflation',12,'input');set('expense',32,'input');set('margin',8,'input');assert.strictEqual(text('premium-index'),'186.7');assert.strictEqual(text('pricing-score'),'78.181');});
check('Reset assumptions restores all controls and price index',()=>{elements['reset-scenario'].fire('click');assert.strictEqual(text('premium-index'),'142.9');assert.deepStrictEqual(['inflation','expense','margin'].map(id=>elements[id].value),['0','25','5']);});
check('Model control uses the GLM final score and age groups',()=>{set('pricing-model','glm');assert.strictEqual(text('pricing-score'),'79.631');assert.strictEqual(elements['calibration-chart'].children.length,7);assert(text('pricing-failure').includes('4.47'));});
check('Risk-decile control displays all ten fixed groups',()=>{set('calibration-view','training_risk_bands');assert.strictEqual(elements['calibration-chart'].children.length,10);assert.strictEqual(elements['calibration-table'].children.length,10);assert.strictEqual(elements['calibration-table'].children[9].children[0].textContent,'D10');});
check('Model switching preserves the selected grouping',()=>{set('pricing-model','hgb');assert.strictEqual(text('pricing-score'),'78.181');assert.strictEqual(elements['calibration-chart'].children.length,10);});
check('Reserve primary 95% display matches 36 of 43',()=>{assert(text('coverage-chart').includes('36/43'));assert(text('coverage-chart').includes('83.7%'));assert.strictEqual(text('reserve-difference'),'+0.001709');});
check('Reserve primary 80% display matches 23 of 43, decision stays at 95%',()=>{set('interval-level','80');assert(text('coverage-chart').includes('23/43'));assert(text('coverage-chart').includes('53.5%'));assert(text('contrast-valuation').includes('95% interval score'));});
check('Reserve secondary 80% display matches 24 of 42',()=>{set('valuation','2009');assert(text('coverage-chart').includes('24/42'));assert(text('coverage-chart').includes('57.1%'));assert(text('reserve-rule-result').includes('cannot override'));});
check('Reserve secondary 95% display matches 32 of 42',()=>{set('interval-level','95');assert(text('coverage-chart').includes('32/42'));assert(text('coverage-chart').includes('76.2%'));assert.strictEqual(text('reserve-difference'),'+0.001664');});
check('Tabs expose the selected panel and update accessibility state',()=>{elements['reserve-tab'].fire('click');assert.strictEqual(elements['reserve-panel'].hidden,false);assert.strictEqual(elements['pricing-panel'].hidden,true);assert.strictEqual(elements['reserve-tab'].getAttribute('aria-selected'),'true');});
check('Keyboard tab navigation and focus are wired',()=>{elements['reserve-tab'].fire('keydown',{key:'ArrowLeft'});assert.strictEqual(elements['pricing-panel'].hidden,false);assert.strictEqual(elements['pricing-tab'].focused,true);assert.strictEqual(elements['pricing-tab'].tabIndex,0);});
const result={date:'2026-10-16',html_sha256:crypto.createHash('sha256').update(html).digest('hex'),checks_passed:checks.length,checks,method:'Actual inline JavaScript executed in Node VM with a minimal DOM harness; checks control wiring, arithmetic and embedded evidence equality.',limitations:['No real browser was available through the supported managed-preview route.','Rendering, CSS layout, actual accessibility-tree behavior and mobile interaction remain unverified.','The DOM harness is not a substitute for final browser QA.'],rendered_browser_verified:false};
fs.writeFileSync(root+'/reports/demo_verification.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({checks_passed:checks.length,rendered_browser_verified:false,html_sha256:result.html_sha256}));
