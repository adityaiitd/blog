/**
 * Paste this into your browser console while logged into
 * https://x.com/i/bookmarks
 *
 * It scrolls, collects ~100 bookmarks, and copies JSON to your clipboard.
 * Then save the clipboard as bookmarks-digest/data/raw-bookmarks.json
 */
(async function exportXBookmarks() {
  const TARGET = 100;
  const MAX_SCROLLS = 40;
  const PAUSE_MS = 1200;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const byId = new Map();

  function scrapeVisible() {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    for (const article of articles) {
      const time = article.querySelector("time");
      const statusLink =
        article.querySelector('a[href*="/status/"]') ||
        (time ? time.closest("a") : null);
      const href = statusLink ? statusLink.href : null;
      if (!href) continue;

      const idMatch = href.match(/status\/(\d+)/);
      const id = idMatch ? idMatch[1] : href;
      if (byId.has(id)) continue;

      const userNameBlock = article.querySelector('[data-testid="User-Name"]');
      const handles = userNameBlock
        ? [...userNameBlock.querySelectorAll('a[href^="/"]')]
            .map((a) => a.getAttribute("href") || "")
            .filter((h) => /^\/[A-Za-z0-9_]+$/.test(h))
        : [];
      const author_handle = handles[0] ? handles[0].slice(1) : "unknown";
      const nameEl = userNameBlock
        ? userNameBlock.querySelector("span")
        : null;
      const author_name = nameEl ? nameEl.textContent.trim() : author_handle;

      const textEl = article.querySelector('[data-testid="tweetText"]');
      const text = textEl ? textEl.innerText.trim() : "";

      const linkEls = article.querySelectorAll('a[href^="http"]');
      const links = [];
      const seen = new Set();
      for (const a of linkEls) {
        const u = a.href;
        if (!u || seen.has(u)) continue;
        if (u.includes("x.com/") || u.includes("twitter.com/")) continue;
        seen.add(u);
        links.push({ url: u, title: (a.innerText || "").trim() });
      }

      // Card / t.co expansions often live in anchors with role presentation
      article.querySelectorAll('a[href*="t.co/"]').forEach((a) => {
        const u = a.href;
        if (!seen.has(u)) {
          seen.add(u);
          links.push({ url: u, title: (a.innerText || "").trim() });
        }
      });

      const media = [...article.querySelectorAll('img[src*="pbs.twimg.com/media"]')]
        .map((img) => img.src)
        .filter(Boolean);

      byId.set(id, {
        id,
        author_name,
        author_handle,
        text,
        url: href.split("?")[0],
        posted_at: time ? time.getAttribute("datetime") : null,
        links,
        media,
      });
    }
  }

  const scroller =
    document.querySelector('[data-testid="primaryColumn"]') ||
    document.scrollingElement ||
    document.documentElement;

  console.log("Starting bookmark export… keep this tab focused.");
  for (let i = 0; i < MAX_SCROLLS && byId.size < TARGET; i++) {
    scrapeVisible();
    console.log(`Collected ${byId.size}/${TARGET} (scroll ${i + 1})`);
    window.scrollBy(0, Math.floor(window.innerHeight * 0.9));
    if (scroller && scroller !== document.scrollingElement) {
      scroller.scrollTop += Math.floor(window.innerHeight * 0.9);
    }
    await sleep(PAUSE_MS);
  }
  scrapeVisible();

  const posts = [...byId.values()].slice(0, TARGET).map((p, idx) => ({
    ...p,
    bookmarked_order: idx + 1,
  }));

  const payload = {
    exported_at: new Date().toISOString(),
    source: "x.com/i/bookmarks",
    count: posts.length,
    posts,
  };

  const json = JSON.stringify(payload, null, 2);
  try {
    await navigator.clipboard.writeText(json);
    console.log(`✅ Copied ${posts.length} bookmarks to clipboard.`);
  } catch (e) {
    console.warn("Clipboard blocked; downloading file instead.", e);
  }

  const blob = new Blob([json], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "raw-bookmarks.json";
  a.click();
  URL.revokeObjectURL(a.href);

  console.log(payload);
  return payload;
})();
