"use strict";(self.webpackChunkdipdup_docs=self.webpackChunkdipdup_docs||[]).push([[105],{6105:(t,e,n)=>{n.r(e),n.d(e,{a:()=>o,s:()=>c});var r=n(7480);function i(t,e){return e.forEach((function(e){e&&"string"!=typeof e&&!Array.isArray(e)&&Object.keys(e).forEach((function(n){if("default"!==n&&!(n in t)){var r=Object.getOwnPropertyDescriptor(e,n);Object.defineProperty(t,n,r.get?r:{enumerable:!0,get:function(){return e[n]}})}}))})),Object.freeze(t)}var o={exports:{}};!function(t){var e,n,r=t.Pos;function i(t,e){for(var n=function(t){var e=t.flags;return null!=e?e:(t.ignoreCase?"i":"")+(t.global?"g":"")+(t.multiline?"m":"")}(t),r=n,i=0;i<e.length;i++)-1==r.indexOf(e.charAt(i))&&(r+=e.charAt(i));return n==r?t:new RegExp(t.source,r)}function o(t){return/\\s|\\n|\n|\\W|\\D|\[\^/.test(t.source)}function h(t,e,n){e=i(e,"g");for(var o=n.line,h=n.ch,c=t.lastLine();o<=c;o++,h=0){e.lastIndex=h;var l=t.getLine(o),s=e.exec(l);if(s)return{from:r(o,s.index),to:r(o,s.index+s[0].length),match:s}}}function c(t,e,n){if(!o(e))return h(t,e,n);e=i(e,"gm");for(var c,l=1,s=n.line,f=t.lastLine();s<=f;){for(var a=0;a<l&&!(s>f);a++){var u=t.getLine(s++);c=null==c?u:c+"\n"+u}l*=2,e.lastIndex=n.ch;var g=e.exec(c);if(g){var p=c.slice(0,g.index).split("\n"),v=g[0].split("\n"),d=n.line+p.length-1,m=p[p.length-1].length;return{from:r(d,m),to:r(d+v.length-1,1==v.length?m+v[0].length:v[v.length-1].length),match:g}}}}function l(t,e,n){for(var r,i=0;i<=t.length;){e.lastIndex=i;var o=e.exec(t);if(!o)break;var h=o.index+o[0].length;if(h>t.length-n)break;(!r||h>r.index+r[0].length)&&(r=o),i=o.index+1}return r}function s(t,e,n){e=i(e,"g");for(var o=n.line,h=n.ch,c=t.firstLine();o>=c;o--,h=-1){var s=t.getLine(o),f=l(s,e,h<0?0:s.length-h);if(f)return{from:r(o,f.index),to:r(o,f.index+f[0].length),match:f}}}function f(t,e,n){if(!o(e))return s(t,e,n);e=i(e,"gm");for(var h,c=1,f=t.getLine(n.line).length-n.ch,a=n.line,u=t.firstLine();a>=u;){for(var g=0;g<c&&a>=u;g++){var p=t.getLine(a--);h=null==h?p:p+"\n"+h}c*=2;var v=l(h,e,f);if(v){var d=h.slice(0,v.index).split("\n"),m=v[0].split("\n"),x=a+d.length,L=d[d.length-1].length;return{from:r(x,L),to:r(x+m.length-1,1==m.length?L+m[0].length:m[m.length-1].length),match:v}}}}function a(t,e,n,r){if(t.length==e.length)return n;for(var i=0,o=n+Math.max(0,t.length-e.length);;){if(i==o)return i;var h=i+o>>1,c=r(t.slice(0,h)).length;if(c==n)return h;c>n?o=h:i=h+1}}function u(t,i,o,h){if(!i.length)return null;var c=h?e:n,l=c(i).split(/\r|\n\r?/);t:for(var s=o.line,f=o.ch,u=t.lastLine()+1-l.length;s<=u;s++,f=0){var g=t.getLine(s).slice(f),p=c(g);if(1==l.length){var v=p.indexOf(l[0]);if(-1==v)continue t;return o=a(g,p,v,c)+f,{from:r(s,a(g,p,v,c)+f),to:r(s,a(g,p,v+l[0].length,c)+f)}}var d=p.length-l[0].length;if(p.slice(d)==l[0]){for(var m=1;m<l.length-1;m++)if(c(t.getLine(s+m))!=l[m])continue t;var x=t.getLine(s+l.length-1),L=c(x),O=l[l.length-1];if(L.slice(0,O.length)==O)return{from:r(s,a(g,p,d,c)+f),to:r(s+l.length-1,a(x,L,O.length,c))}}}}function g(t,i,o,h){if(!i.length)return null;var c=h?e:n,l=c(i).split(/\r|\n\r?/);t:for(var s=o.line,f=o.ch,u=t.firstLine()-1+l.length;s>=u;s--,f=-1){var g=t.getLine(s);f>-1&&(g=g.slice(0,f));var p=c(g);if(1==l.length){var v=p.lastIndexOf(l[0]);if(-1==v)continue t;return{from:r(s,a(g,p,v,c)),to:r(s,a(g,p,v+l[0].length,c))}}var d=l[l.length-1];if(p.slice(0,d.length)==d){var m=1;for(o=s-l.length+1;m<l.length-1;m++)if(c(t.getLine(o+m))!=l[m])continue t;var x=t.getLine(s+1-l.length),L=c(x);if(L.slice(L.length-l[0].length)==l[0])return{from:r(s+1-l.length,a(x,L,x.length-l[0].length,c)),to:r(s,a(g,p,d.length,c))}}}}function p(t,e,n,o){var l;this.atOccurrence=!1,this.afterEmptyMatch=!1,this.doc=t,n=n?t.clipPos(n):r(0,0),this.pos={from:n,to:n},"object"==typeof o?l=o.caseFold:(l=o,o=null),"string"==typeof e?(null==l&&(l=!1),this.matches=function(n,r){return(n?g:u)(t,e,r,l)}):(e=i(e,"gm"),o&&!1===o.multiline?this.matches=function(n,r){return(n?s:h)(t,e,r)}:this.matches=function(n,r){return(n?f:c)(t,e,r)})}String.prototype.normalize?(e=function(t){return t.normalize("NFD").toLowerCase()},n=function(t){return t.normalize("NFD")}):(e=function(t){return t.toLowerCase()},n=function(t){return t}),p.prototype={findNext:function(){return this.find(!1)},findPrevious:function(){return this.find(!0)},find:function(e){var n=this.doc.clipPos(e?this.pos.from:this.pos.to);if(this.afterEmptyMatch&&this.atOccurrence&&(n=r(n.line,n.ch),e?(n.ch--,n.ch<0&&(n.line--,n.ch=(this.doc.getLine(n.line)||"").length)):(n.ch++,n.ch>(this.doc.getLine(n.line)||"").length&&(n.ch=0,n.line++)),0!=t.cmpPos(n,this.doc.clipPos(n))))return this.atOccurrence=!1;var i=this.matches(e,n);if(this.afterEmptyMatch=i&&0==t.cmpPos(i.from,i.to),i)return this.pos=i,this.atOccurrence=!0,this.pos.match||!0;var o=r(e?this.doc.firstLine():this.doc.lastLine()+1,0);return this.pos={from:o,to:o},this.atOccurrence=!1},from:function(){if(this.atOccurrence)return this.pos.from},to:function(){if(this.atOccurrence)return this.pos.to},replace:function(e,n){if(this.atOccurrence){var i=t.splitLines(e);this.doc.replaceRange(i,this.pos.from,this.pos.to,n),this.pos.to=r(this.pos.from.line+i.length-1,i[i.length-1].length+(1==i.length?this.pos.from.ch:0))}}},t.defineExtension("getSearchCursor",(function(t,e,n){return new p(this.doc,t,e,n)})),t.defineDocExtension("getSearchCursor",(function(t,e,n){return new p(this,t,e,n)})),t.defineExtension("selectMatches",(function(e,n){for(var r=[],i=this.getSearchCursor(e,this.getCursor("from"),n);i.findNext()&&!(t.cmpPos(i.to(),this.getCursor("to"))>0);)r.push({anchor:i.from(),head:i.to()});r.length&&this.setSelections(r,0)}))}(r.a.exports);var h=o.exports,c=Object.freeze(i({__proto__:null,[Symbol.toStringTag]:"Module",default:h},[o.exports]))}}]);