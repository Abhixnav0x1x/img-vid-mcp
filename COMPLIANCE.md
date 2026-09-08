# COMPLIANCE — scraping vs using

Scraping public result URLs/metadata is low-risk (facts aren't copyrightable; cf. hiQ v. LinkedIn; 2026 SerpApi/Google DMCA limits on plain results). **Using images/videos is separate risk.**

Rules built into imagemcp:
1. Default `license_image=ShareCommercially`. Prefer `Public` for commercial hero assets.
2. Never hotlink — always `download_media`; keep `source_page` in `credits.json`.
3. Blocked: private IPs, localhost, login-walled (FB/IG) — pick another result or embed.
4. Google Images keyword path uses `tbs=il:cl` (Creative Commons) in Camoufox mode.
5. Video: `download_video` saves a local file. Only download videos you hold rights to
   (your own uploads, Creative Commons, explicit license). YouTube's ToS restricts
   downloading — the operator/agent owns that decision. When in doubt, embed instead.

You are responsible for downstream use. When in doubt: Wikimedia Commons / Openverse / Pexels CDN over random blogs. This file is info, not legal advice.
