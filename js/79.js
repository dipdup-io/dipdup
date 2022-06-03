"use strict";(self.webpackChunkdipdup_docs=self.webpackChunkdipdup_docs||[]).push([[79],{6079:(t,e,i)=>{function n(t,e){return e.forEach((function(e){e&&"string"!=typeof e&&!Array.isArray(e)&&Object.keys(e).forEach((function(i){if("default"!==i&&!(i in t)){var n=Object.getOwnPropertyDescriptor(e,i);Object.defineProperty(t,i,n.get?n:{enumerable:!0,get:function(){return e[i]}})}}))})),Object.freeze(t)}i.r(e),i.d(e,{s:()=>r});var o={exports:{}};!function(t){function e(t,e){if(this.cm=t,this.options=e,this.widget=null,this.debounce=0,this.tick=0,this.startPos=this.cm.getCursor("start"),this.startLen=this.cm.getLine(this.startPos.line).length-this.cm.getSelection().length,this.options.updateOnCursorActivity){var i=this;t.on("cursorActivity",this.activityFunc=function(){i.cursorActivity()})}}t.showHint=function(t,e,i){if(!e)return t.showHint(i);i&&i.async&&(e.async=!0);var n={hint:e};if(i)for(var o in i)n[o]=i[o];return t.showHint(n)},t.defineExtension("showHint",(function(i){i=function(t,e,i){var n=t.options.hintOptions,o={};for(var s in l)o[s]=l[s];if(n)for(var s in n)void 0!==n[s]&&(o[s]=n[s]);if(i)for(var s in i)void 0!==i[s]&&(o[s]=i[s]);return o.hint.resolve&&(o.hint=o.hint.resolve(t,e)),o}(this,this.getCursor("start"),i);var n=this.listSelections();if(!(n.length>1)){if(this.somethingSelected()){if(!i.hint.supportsSelection)return;for(var o=0;o<n.length;o++)if(n[o].head.line!=n[o].anchor.line)return}this.state.completionActive&&this.state.completionActive.close();var s=this.state.completionActive=new e(this,i);s.options.hint&&(t.signal(this,"startCompletion",this),s.update(!0))}})),t.defineExtension("closeHint",(function(){this.state.completionActive&&this.state.completionActive.close()}));var i=window.requestAnimationFrame||function(t){return setTimeout(t,1e3/60)},n=window.cancelAnimationFrame||clearTimeout;function o(t){return"string"==typeof t?t:t.text}function s(t,e){for(;e&&e!=t;){if("LI"===e.nodeName.toUpperCase()&&e.parentNode==t)return e;e=e.parentNode}}function r(e,i){this.id="cm-complete-"+Math.floor(Math.random(1e6)),this.completion=e,this.data=i,this.picked=!1;var n=this,r=e.cm,c=r.getInputField().ownerDocument,l=c.defaultView||c.parentWindow,h=this.hints=c.createElement("ul");h.setAttribute("role","listbox"),h.setAttribute("aria-expanded","true"),h.id=this.id;var a=e.cm.options.theme;h.className="CodeMirror-hints "+a,this.selectedHint=i.selectedHint||0;for(var u=i.list,f=0;f<u.length;++f){var d=h.appendChild(c.createElement("li")),p=u[f],m="CodeMirror-hint"+(f!=this.selectedHint?"":" CodeMirror-hint-active");null!=p.className&&(m=p.className+" "+m),d.className=m,f==this.selectedHint&&d.setAttribute("aria-selected","true"),d.id=this.id+"-"+f,d.setAttribute("role","option"),p.render?p.render(d,i,p):d.appendChild(c.createTextNode(p.displayText||o(p))),d.hintId=f}var g=e.options.container||c.body,v=r.cursorCoords(e.options.alignWithWord?i.from:null),y=v.left,b=v.bottom,w=!0,A=0,H=0;if(g!==c.body){var C=-1!==["absolute","relative","fixed"].indexOf(l.getComputedStyle(g).position)?g:g.offsetParent,k=C.getBoundingClientRect(),x=c.body.getBoundingClientRect();A=k.left-x.left-C.scrollLeft,H=k.top-x.top-C.scrollTop}h.style.left=y-A+"px",h.style.top=b-H+"px";var O=l.innerWidth||Math.max(c.body.offsetWidth,c.documentElement.offsetWidth),S=l.innerHeight||Math.max(c.body.offsetHeight,c.documentElement.offsetHeight);g.appendChild(h),r.getInputField().setAttribute("aria-autocomplete","list"),r.getInputField().setAttribute("aria-owns",this.id),r.getInputField().setAttribute("aria-activedescendant",this.id+"-"+this.selectedHint);var T,M=e.options.moveOnOverlap?h.getBoundingClientRect():new DOMRect,F=!!e.options.paddingForScrollbar&&h.scrollHeight>h.clientHeight+1;if(setTimeout((function(){T=r.getScrollInfo()})),M.bottom-S>0){var N=M.bottom-M.top;if(v.top-(v.bottom-M.top)-N>0)h.style.top=(b=v.top-N-H)+"px",w=!1;else if(N>S){h.style.height=S-5+"px",h.style.top=(b=v.bottom-M.top-H)+"px";var P=r.getCursor();i.from.ch!=P.ch&&(v=r.cursorCoords(P),h.style.left=(y=v.left-A)+"px",M=h.getBoundingClientRect())}}var E,I=M.right-O;if(F&&(I+=r.display.nativeBarWidth),I>0&&(M.right-M.left>O&&(h.style.width=O-5+"px",I-=M.right-M.left-O),h.style.left=(y=v.left-I-A)+"px"),F)for(var W=h.firstChild;W;W=W.nextSibling)W.style.paddingRight=r.display.nativeBarWidth+"px";r.addKeyMap(this.keyMap=function(t,e){var i={Up:function(){e.moveFocus(-1)},Down:function(){e.moveFocus(1)},PageUp:function(){e.moveFocus(1-e.menuSize(),!0)},PageDown:function(){e.moveFocus(e.menuSize()-1,!0)},Home:function(){e.setFocus(0)},End:function(){e.setFocus(e.length-1)},Enter:e.pick,Tab:e.pick,Esc:e.close};/Mac/.test(navigator.platform)&&(i["Ctrl-P"]=function(){e.moveFocus(-1)},i["Ctrl-N"]=function(){e.moveFocus(1)});var n=t.options.customKeys,o=n?{}:i;function s(t,n){var s;s="string"!=typeof n?function(t){return n(t,e)}:i.hasOwnProperty(n)?i[n]:n,o[t]=s}if(n)for(var r in n)n.hasOwnProperty(r)&&s(r,n[r]);var c=t.options.extraKeys;if(c)for(var r in c)c.hasOwnProperty(r)&&s(r,c[r]);return o}(e,{moveFocus:function(t,e){n.changeActive(n.selectedHint+t,e)},setFocus:function(t){n.changeActive(t)},menuSize:function(){return n.screenAmount()},length:u.length,close:function(){e.close()},pick:function(){n.pick()},data:i})),e.options.closeOnUnfocus&&(r.on("blur",this.onBlur=function(){E=setTimeout((function(){e.close()}),100)}),r.on("focus",this.onFocus=function(){clearTimeout(E)})),r.on("scroll",this.onScroll=function(){var t=r.getScrollInfo(),i=r.getWrapperElement().getBoundingClientRect();T||(T=r.getScrollInfo());var n=b+T.top-t.top,o=n-(l.pageYOffset||(c.documentElement||c.body).scrollTop);if(w||(o+=h.offsetHeight),o<=i.top||o>=i.bottom)return e.close();h.style.top=n+"px",h.style.left=y+T.left-t.left+"px"}),t.on(h,"dblclick",(function(t){var e=s(h,t.target||t.srcElement);e&&null!=e.hintId&&(n.changeActive(e.hintId),n.pick())})),t.on(h,"click",(function(t){var i=s(h,t.target||t.srcElement);i&&null!=i.hintId&&(n.changeActive(i.hintId),e.options.completeOnSingleClick&&n.pick())})),t.on(h,"mousedown",(function(){setTimeout((function(){r.focus()}),20)}));var R=this.getSelectedHintRange();return 0===R.from&&0===R.to||this.scrollToActive(),t.signal(i,"select",u[this.selectedHint],h.childNodes[this.selectedHint]),!0}function c(t,e,i,n){if(t.async)t(e,n,i);else{var o=t(e,i);o&&o.then?o.then(n):n(o)}}e.prototype={close:function(){this.active()&&(this.cm.state.completionActive=null,this.tick=null,this.options.updateOnCursorActivity&&this.cm.off("cursorActivity",this.activityFunc),this.widget&&this.data&&t.signal(this.data,"close"),this.widget&&this.widget.close(),t.signal(this.cm,"endCompletion",this.cm))},active:function(){return this.cm.state.completionActive==this},pick:function(e,i){var n=e.list[i],s=this;this.cm.operation((function(){n.hint?n.hint(s.cm,e,n):s.cm.replaceRange(o(n),n.from||e.from,n.to||e.to,"complete"),t.signal(e,"pick",n),s.cm.scrollIntoView()})),this.options.closeOnPick&&this.close()},cursorActivity:function(){this.debounce&&(n(this.debounce),this.debounce=0);var t=this.startPos;this.data&&(t=this.data.from);var e=this.cm.getCursor(),o=this.cm.getLine(e.line);if(e.line!=this.startPos.line||o.length-e.ch!=this.startLen-this.startPos.ch||e.ch<t.ch||this.cm.somethingSelected()||!e.ch||this.options.closeCharacters.test(o.charAt(e.ch-1)))this.close();else{var s=this;this.debounce=i((function(){s.update()})),this.widget&&this.widget.disable()}},update:function(t){if(null!=this.tick){var e=this,i=++this.tick;c(this.options.hint,this.cm,this.options,(function(n){e.tick==i&&e.finishUpdate(n,t)}))}},finishUpdate:function(e,i){this.data&&t.signal(this.data,"update");var n=this.widget&&this.widget.picked||i&&this.options.completeSingle;this.widget&&this.widget.close(),this.data=e,e&&e.list.length&&(n&&1==e.list.length?this.pick(e,0):(this.widget=new r(this,e),t.signal(e,"shown")))}},r.prototype={close:function(){if(this.completion.widget==this){this.completion.widget=null,this.hints.parentNode&&this.hints.parentNode.removeChild(this.hints),this.completion.cm.removeKeyMap(this.keyMap);var t=this.completion.cm.getInputField();t.removeAttribute("aria-activedescendant"),t.removeAttribute("aria-owns");var e=this.completion.cm;this.completion.options.closeOnUnfocus&&(e.off("blur",this.onBlur),e.off("focus",this.onFocus)),e.off("scroll",this.onScroll)}},disable:function(){this.completion.cm.removeKeyMap(this.keyMap);var t=this;this.keyMap={Enter:function(){t.picked=!0}},this.completion.cm.addKeyMap(this.keyMap)},pick:function(){this.completion.pick(this.data,this.selectedHint)},changeActive:function(e,i){if(e>=this.data.list.length?e=i?this.data.list.length-1:0:e<0&&(e=i?0:this.data.list.length-1),this.selectedHint!=e){var n=this.hints.childNodes[this.selectedHint];n&&(n.className=n.className.replace(" CodeMirror-hint-active",""),n.removeAttribute("aria-selected")),(n=this.hints.childNodes[this.selectedHint=e]).className+=" CodeMirror-hint-active",n.setAttribute("aria-selected","true"),this.completion.cm.getInputField().setAttribute("aria-activedescendant",n.id),this.scrollToActive(),t.signal(this.data,"select",this.data.list[this.selectedHint],n)}},scrollToActive:function(){var t=this.getSelectedHintRange(),e=this.hints.childNodes[t.from],i=this.hints.childNodes[t.to],n=this.hints.firstChild;e.offsetTop<this.hints.scrollTop?this.hints.scrollTop=e.offsetTop-n.offsetTop:i.offsetTop+i.offsetHeight>this.hints.scrollTop+this.hints.clientHeight&&(this.hints.scrollTop=i.offsetTop+i.offsetHeight-this.hints.clientHeight+n.offsetTop)},screenAmount:function(){return Math.floor(this.hints.clientHeight/this.hints.firstChild.offsetHeight)||1},getSelectedHintRange:function(){var t=this.completion.options.scrollMargin||0;return{from:Math.max(0,this.selectedHint-t),to:Math.min(this.data.list.length-1,this.selectedHint+t)}}},t.registerHelper("hint","auto",{resolve:function(e,i){var n,o=e.getHelpers(i,"hint");if(o.length){var s=function(t,e,i){var n=function(t,e){if(!t.somethingSelected())return e;for(var i=[],n=0;n<e.length;n++)e[n].supportsSelection&&i.push(e[n]);return i}(t,o);!function o(s){if(s==n.length)return e(null);c(n[s],t,i,(function(t){t&&t.list.length>0?e(t):o(s+1)}))}(0)};return s.async=!0,s.supportsSelection=!0,s}return(n=e.getHelper(e.getCursor(),"hintWords"))?function(e){return t.hint.fromList(e,{words:n})}:t.hint.anyword?function(e,i){return t.hint.anyword(e,i)}:function(){}}}),t.registerHelper("hint","fromList",(function(e,i){var n,o=e.getCursor(),s=e.getTokenAt(o),r=t.Pos(o.line,s.start),c=o;s.start<o.ch&&/\w/.test(s.string.charAt(o.ch-s.start-1))?n=s.string.substr(0,o.ch-s.start):(n="",r=o);for(var l=[],h=0;h<i.words.length;h++){var a=i.words[h];a.slice(0,n.length)==n&&l.push(a)}if(l.length)return{list:l,from:r,to:c}})),t.commands.autocomplete=t.showHint;var l={hint:t.hint.auto,completeSingle:!0,alignWithWord:!0,closeCharacters:/[\s()\[\]{};:>,]/,closeOnPick:!0,closeOnUnfocus:!0,updateOnCursorActivity:!0,completeOnSingleClick:!0,container:null,customKeys:null,extraKeys:null,paddingForScrollbar:!0,moveOnOverlap:!0};t.defineOption("hintOptions",null)}(i(7480).a.exports);var s=o.exports,r=Object.freeze(n({__proto__:null,[Symbol.toStringTag]:"Module",default:s},[o.exports]))}}]);