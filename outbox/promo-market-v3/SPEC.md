# Promo Market v3: changes on top of v2 (ET-32929)

Draft, not filed. The look is THEIR live page with these changes on it: `python outbox/promo-market-v3/live/serve.py`,
then http://127.0.0.1:8792/expire76#new (the owner) and http://127.0.0.1:8792/promo-market (a stranger). Pictures:
`python outbox/promo-market-v3/live/render.py` → `pictures/` (not in git; made again in a minute).

Asked by the operator on 2026-10-27. Everything below is a patch on v2; what is not named stays as it is.

## A. The product's own address, and its maker
1. **`cymetica.com/promo-market`** opens the market (the Market tab) for anybody, signed in or not. It is the product's
   address. `/creator-dashboard` (the link in the daily Telegram post) keeps opening a member's dashboard as today.
2. **The Universe says *Made by BJ Ironstar Capital*** on the Promo Market building and its panel (today: Cymetica).
   It is BJ Ironstar Capital's product; Cymetica's part is the creator dashboard.

## B. Post a brief (`#new`)
3. **Any website, not only an app on Cymetica.** First tile of the picker: *My own website* → a name and a URL. Picked
   (or when the owner has no products), the brief promotes that URL; the POST carries `url` and `name` in place of
   `product_path`. *Per new user* is off for such a brief until the site carries Cymetica's sign-up tag.
4. **Every price says its unit.** Each price field ends in `USDC`; under a dollar it also says cents (`0.05 USDC = 5 ¢`).
   One line above the prices: *all prices in USDC (1 USDC = $1)*. The brief card says the same: `per 1k views`,
   `per new user`, `per visitor = 5 ¢`.
5. **Cover picture** in place of *Picture for posts*: the picture that goes with every promoter's post; by default a
   screenshot of the product page, replaced by the first picture the owner drops. Shown 132×74, its line wraps.
6. **The link field is full width** (today it is the width of the icon column: `https:/`).
7. **Per new user says the rule that counts**: *spends ≥ this on Cymetica in 14 days · a deposit alone never counts*.
   Today the label says *own deposit* and only the tooltip says the fees rule (your `/api/v1/promo/how-counted`, *Costs
   more to fake than it pays*). The same text in the brief's drawer.
8. **Per unique visitor** in place of *Per new visitor*: one real person's first visit, paid after 7 days (your rule).

## C. A post is paid by its reach
9. **The price of a post is a rate**: USDC per 1,000 real views of the post, up to a *max for one post*. Default 3 USDC
   per 1,000 views, max 40.
10. **Who may apply**, set by the owner, measured by Cymetica on X: average views of the last 20 posts, followers, account
    age in days, real audience in %. The form shows what the rate pays an example account (*6,800 avg views: 20.40 USDC*).
11. **A promoter applies with their X account** (*Apply with your X* on the card, in place of *Take it*). Cymetica reads
    the account and drops those under the owner's bar and the fakes: bought followers (views far under followers), new
    accounts, one device or wallet behind two promoters. Followers alone never decide it.
12. **The owner approves.** A bell in the top bar counts promoters waiting; it opens *Promoters who want your brief*: per
    promoter followers, average views, engagement, real audience, account age, a reach score 0-100, and the price by reach;
    the owner accepts at that price or types their own, or declines. *Filtered out by Cymetica* lists who was dropped and
    why. An accepted promoter gets their own link; the post is paid once it has stayed up 7 days, at the accepted price.
    How reach is measured and how fakes are caught is yours; the rule is only that a farmed account must cost more than
    it earns.

## D. User protection on the market
13. **A band above Open briefs**: *Only real people are paid for*, four numbers (checks on every visitor and user, checks
    on every promoter, 7 days before a visitor is paid, 14 days before a user is paid) and two lanes of checks: the
    promoter checks of C, and your own counting rules from `/api/v1/promo/how-counted`, each with its text on hover.
