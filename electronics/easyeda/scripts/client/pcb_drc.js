async function waitReady() { try { await eda.dmt_Project.waitForReady(); } catch (e) { /* older builds */ } }
await waitReady();
let pcbs = await eda.dmt_Pcb.getAllPcbsInfo();
for (let i = 0; i < 40 && (!Array.isArray(pcbs) || pcbs.length === 0); i += 1) {
  await new Promise((r) => setTimeout(r, 750));
  pcbs = await eda.dmt_Pcb.getAllPcbsInfo();
}
if (!Array.isArray(pcbs) || !pcbs.length) throw new Error('no PCB in project');
await eda.dmt_EditorControl.openDocument(pcbs[0].uuid);
await new Promise((r) => setTimeout(r, 1500));
const details = await eda.pcb_Drc.check(true, false, true);
const passed = await eda.pcb_Drc.check(true, false, false);
const groups = Array.isArray(details) ? details : [];
const summary = groups.map((g) => ({ name: Array.isArray(g.title) ? g.title.join(' ') : (g.name || ''), count: g.count }));
let total = 0;
const walk = (arr) => { for (const g of arr || []) { if (Array.isArray(g.list)) walk(g.list); else if (typeof g.count === 'number') total += g.count; } };
walk(groups);
return { pcb: pcbs[0].name, passed, total, summary };
