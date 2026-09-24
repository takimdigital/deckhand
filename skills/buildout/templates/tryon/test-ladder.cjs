/**
 * Slot-ladder test — extracts the LADDER-* block from the SHIPPED overlay.js (never a copy) and
 * runs it over fixtures shaped like the elements a real app has: a pricing grid of tier cards,
 * one tier card, the CTA inside a card, a header, a header button, an FAQ list, a footer.
 *
 *   node templates/tryon/test-ladder.cjs            # exits 0 = all pass
 *
 * The fixtures are measured shapes from a live Next.js app (shadcn-style markup, data-slot on
 * buttons, bg-card on cards) — if the ladder drifts, this fails before a browser ever loads it.
 */
const fs = require("fs");
const path = require("path");

const OVERLAY = path.join(__dirname, "overlay.js");
const src = fs.readFileSync(OVERLAY, "utf8");
const start = src.indexOf("/* LADDER-START");
const end = src.indexOf("/* LADDER-END */");
if (start === -1 || end === -1 || end < start) {
  console.error("FAIL: LADDER-START / LADDER-END markers are missing from overlay.js — the test cannot extract the ladder.");
  process.exit(1);
}
const commentEnd = src.indexOf("*/", start);
const factory = new Function(src.slice(commentEnd + 2, end) + "\nreturn { guessSlot: guessSlot, pathSlot: pathSlot };");
const ladder = factory();

/* ------------------------------------------------------------------ mini DOM */
function mk(tag, attrs, kids, text) {
  const n = {
    nodeType: 1,
    tagName: tag.toUpperCase(),
    children: [],
    parentElement: null,
    _a: attrs || {},
    _t: text || "",
    getAttribute(k) { return k in this._a ? this._a[k] : null; },
  };
  (kids || []).forEach((k) => { k.parentElement = n; n.children.push(k); });
  Object.defineProperty(n, "textContent", {
    get() { return [this._t].concat(this.children.map((c) => c.textContent)).join(" "); },
  });
  return n;
}
function tree(root, ...body) { let cur = mk("div", { class: "root" }, [root]); return cur; }

/* ------------------------------------------------------------------ fixtures (measured shapes) */
const tierCard = (name, price, cta) => mk("div", { class: "relative flex flex-col rounded-2xl p-6 bg-card" }, [
  mk("div", { class: "text-lg font-semibold" }, [], name),
  mk("div", { class: "text-3xl font-bold" }, [], price),
  mk("a", { "data-slot": "button", href: "/quiz" }, [], cta),
]);
const cardA = tierCard("Gratuit", "$0", "Commencer gratuitement");
const cardB = tierCard("Pro", "$12", "Passer au Pro");
const cardC = tierCard("Agence", "$29", "Contacter");
const grid = mk("div", { class: "grid items-stretch gap-5 sm:grid-cols-2 md:gap-6" }, [cardA, cardB, cardC]);
const pageContainer = mk("div", { class: "mx-auto max-w-4xl" }, [grid]);
const main = mk("main", { id: "main", class: "flex-1" }, [pageContainer]);
const rootDiv = mk("div", { class: "flex min-h-screen flex-col" }, [main]);

const headerBtn = mk("button", { class: "rounded-md bg-primary px-4" }, [], "Sign in");
const header = mk("header", { class: "sticky top-0 z-40 border-b border-border bg-background" }, [
  mk("nav", { class: "mx-auto flex items-center justify-between" }, [headerBtn]),
]);
const footerLink = mk("a", { href: "/privacy", class: "text-sm text-muted-foreground" }, [], "Privacy");
const footer = mk("footer", { class: "border-t border-border bg-card" }, [
  mk("nav", { class: "flex gap-4" }, [footerLink]),
]);

const faqPair = (q) => mk("div", { class: "space-y-2" }, [
  mk("dt", { class: "font-medium" }, [], q + "?"),
  mk("dd", { class: "text-muted-foreground" }, [], "Reponse courte."),
]);
const faqDl = mk("dl", { class: "mt-4 space-y-5" }, [faqPair("Est-ce gratuit"), faqPair("Puis-je annuler"), faqPair("Combien de questions")]);
const faqSecond = mk("dl", { class: "mt-4" }, [
  mk("dt", {}, [], "Question une ?"), mk("dd", {}, [], "A un."),
  mk("dt", {}, [], "Question deux ?"), mk("dd", {}, [], "A deux."),
]);
const faqWrapper = mk("section", { class: "mt-16" }, [mk("h2", { class: "text-2xl font-bold" }, [], "Questions frequentes"), faqDl]);
const bareSpan = mk("span", { class: "inline-flex" }, [], "hello");
const headerSpan = mk("span", { class: "sr-only" }, [], "menu");
header.children[0].children.push(headerSpan);
// real pages nest: a click lands on a span 4 levels above its card — the walk must reach it
const deepSpan = mk("span", { class: "text-sm" }, [], "$12");
const deepCard = mk("div", { class: "relative flex flex-col rounded-2xl p-6 bg-card" }, [
  mk("div", { class: "flex items-baseline gap-1" }, [mk("div", { class: "flex flex-col" }, [mk("div", { class: "text-lg font-semibold" }, [], "Pro"), deepSpan])]),
  mk("a", { "data-slot": "button", href: "/x" }, [], "Choisir"),
]);
const deepGrid = mk("div", { class: "grid items-stretch gap-5" }, [deepCard, tierCard("Agence", "$29", "Contacter")]);

/* ------------------------------------------------------------------ assertions */
let pass = 0, fail = 0;
function is(node, slot, label) {
  const g = ladder.guessSlot(node);
  const got = g ? g.slot : null;
  const okk = got === slot;
  console.log((okk ? "  ok   " : "  FAIL ") + label + " -> " + got + (okk ? "" : " (expected " + slot + ")" + (g ? " [" + g.why + "]" : "")));
  okk ? pass++ : fail++;
}
function isPath(input, slot, label) {
  const got = ladder.pathSlot(input);
  const okk = got === slot;
  console.log((okk ? "  ok   " : "  FAIL ") + label + " -> " + got + (okk ? "" : " (expected " + slot + ")"));
  okk ? pass++ : fail++;
}
console.log("slot ladder over measured element shapes:");
is(grid, "pricing", "pricing grid container");
is(cardB, "card", "one tier card inside the grid");
is(cardB.children[2], "button", "the CTA button inside a tier card");
is(header, "navbar", "site header wrapper");
is(headerBtn, "button", "plain button in the header");
is(faqDl, "faq", "FAQ list (wrapped question/answer pairs)");
is(faqSecond, "faq", "FAQ list (direct dt/dd pairs)");
is(footer, "footer", "footer");
is(footerLink, "footer", "a link inside the footer");
is(faqDl.children[0].children[0], "faq", "a single question term inside the FAQ");
is(deepSpan, "card", "a span nested 4 levels inside its priced card");
is(deepGrid, "pricing", "a grid of deeply nested priced cards");
is(faqWrapper, null, "the FAQ SECTION wrapper stays unknown (documented)");
is(pageContainer, null, "the page container is not a slot");
is(bareSpan, null, "an unremarkable span stays unknown");
is(rootDiv, null, "the page root is not a slot");
isPath("/x/components/SiteHeader.tsx", "navbar", "pathSlot still reads component file names");
isPath("/x/app/(dashboard)/pricing/page.tsx", null, "pathSlot refuses to guess from page.tsx");

console.log(pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
