import React from 'react';
import { Document, Page, Text, View, StyleSheet, renderToBuffer } from '@react-pdf/renderer';
const e=React.createElement;
const s=StyleSheet.create({page:{padding:36,fontSize:10,fontFamily:'Helvetica'},h1:{fontSize:18,marginBottom:14},h2:{fontSize:13,marginTop:12,marginBottom:6},row:{marginBottom:4},box:{padding:8,backgroundColor:'#f3f4f6',marginBottom:6},warn:{padding:8,backgroundColor:'#fff4ce',marginTop:12},mono:{fontFamily:'Courier',fontSize:7}});
const short=(v)=>v?`${v.slice(0,18)}…${v.slice(-10)}`:'—';
export async function renderAuditPdf(proof){
 const ladder=proof.merkle.ladder.map((r)=>e(View,{style:s.box,key:r.level},e(Text,null,`Level ${r.level}: sibling on ${r.siblingSide}`),e(Text,{style:s.mono},`Sibling ${short(r.sibling)}`),e(Text,{style:s.mono},`Computed parent ${short(r.computedParent)}`)));
 const page=e(Page,{size:'A4',style:s.page},e(Text,{style:s.h1},`Audit Report - Agent Session #${proof.sessionId}`),e(Text,{style:s.row},`Proof ID: ${proof.id}`),e(Text,{style:s.row},`Observed: ${new Date(proof.observedAt).toISOString()}`),e(Text,{style:s.row},`Target: ${proof.url}`),e(Text,{style:s.row},`Status: ${proof.status} (${proof.source.state} snapshot)`),e(Text,{style:s.h2},'Local Merkle authentication path'),e(Text,{style:s.mono},`Leaf ${proof.merkle.leafHash}`),...ladder,e(Text,{style:s.mono},`Expected root ${proof.merkle.root}`),e(Text,null,`Local root match: ${proof.merkle.valid?'YES':'NO'}`),e(Text,{style:s.h2},'L2 anchoring'),e(Text,null,`Chain: ${proof.chain}`),e(Text,null,`Transaction: ${proof.l2TransactionHash||'Not recorded'}`),e(Text,{style:s.warn},proof.disclaimer),e(Text,{style:s.row},'Raw proof payload is intentionally excluded from this report.'));
 return renderToBuffer(e(Document,{title:`Audit Report - Agent Session #${proof.sessionId}`},page));
}
