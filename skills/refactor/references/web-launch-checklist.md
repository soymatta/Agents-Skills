# Web launch checklist

Mirror of the 20-item business-website launch checklist, kept here so
`refactor` can run it offline or standalone. When the `web-esenciales` skill is
installed it is the source of truth: reuse its report instead of repeating the
audit.

Verify each item under the matching axis (almost all is `architecture` or
`security`; nothing changes visible behavior except `security`). Mark each ✔/✘
with `file:line` or command.

Indexing and search:

1. No leftover `noindex` in prod (neither meta nor `X-Robots-Tag` nor
   `Disallow: /` in `robots.txt`).
2. Search Console signup (verified property) + sitemap submitted.
3. Bing Webmaster Tools signup (verified property) + sitemap submitted.

URLs and links:

4. Single domain version (with/without `www` + `http`→`https` with 301).
5. Real 301 redirects for old/changed URLs (no 302, no meta-refresh).
6. Canonical URLs (absolute `rel="canonical"`, one per page).
7. Clean URLs (readable, lowercase, no IDs or session params).
8. Internal link hierarchy (every page ≤3 clicks from home, no orphans,
   no redirect chains).
9. One page per search intent (no cannibalization between URLs).

Contact and social:

10. Tappable phone (`tel:`) and email (`mailto:`) on mobile and desktop.
11. Real social icons (point to the profiles, not to `#`).
12. Share preview (Open Graph + Twitter Card with absolute image
    ≥1200×630, title and description per page).

Infra:

13. Cache configured (hashed statics + `Cache-Control`, HTML revalidated).
14. Valid SSL with auto-renewal (expiry >30 days + cron/timer verified).
15. Automatic backups (what, how often, where, retention).
16. Downtime alerts (uptime monitor with alerts to the owner's channel).

Content and validation:

17. Test content removed (lorem, watermarked stock, demo users).
18. Tested in several browsers (Chromium + Firefox + WebKit, zero console errors).
19. Thank-you page after every form (conversion confirmed + no resubmit on reload).
20. Conversions measured (analytics event on each goal: form, call, purchase).
