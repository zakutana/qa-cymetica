# Promo Market v3: changes on top of v2 (ET-32929)

The build spec for the Build it Better request in [`build-it-better/request.txt`](build-it-better/request.txt).
Pictures: [`build-it-better/pictures/`](build-it-better/pictures/) ("picture N" below means `N-*.webp`), taken at
2000 px wide from your own live v2 page with these changes on it.

**We give only the look. The look is binding; how it works is yours**: how reach is measured, how fakes are caught,
what a check says, and every word the page shows about protection is for you to write and secure. Where your backend
cannot do what is drawn, change the design as little as it takes and name each change in your BB-SPEC.

**The look is code on top of your own file**, so nothing has to be redrawn:
- [`live/v3.js`](live/v3.js) goes at the end of the closure in your `promo_market_v2.js` (before `route(false);
  bootStart();`). Its functions replace yours of the same name (`chrome`, `defaultForm`, `formBrief`, `briefCard`,
  `newBrief`, `ownerBrief`); the rest is new (`v3OfferBox`, `v3Offers`, `v3Promoters`, `v3Chart`, `v3Protect`). It
  calls your helpers as they are.
- [`live/v3.css`](live/v3.css) loads after `promo_market_v2.css`.
- [`live/patch.py`](live/patch.py), `JS_ANCHORS`: the five small text changes in your own file (the band above Open
  briefs, the offer box in the brief's drawer, the post's price left out where it is priced by reach, two labels).
- [`live/sample.py`](live/sample.py): the sample brief the pictures show (one brief, five promoters with handles ending
  `_demo`, invented numbers). The fields it adds to your answers are the ones the new screens read.

Everything below is a patch on v2; what is not named stays as it is.

## A. The product's own address, and its maker
1. **`cymetica.com/promo-market`** opens the Market tab for anybody, signed in or not: it is the product's address.
   `/creator-dashboard` (the link in the daily Telegram post) keeps opening a member's dashboard as today.
2. **The Universe says *Made by BJ Ironstar Capital*** on the Promo Market building and its panel (today: Cymetica).

## B. Post a brief (`#new`, pictures 1, 2)
3. **Any website, not only an app on Cymetica.** The first tile of the picker is *My own website*: a name and a URL.
   Picked, or when the owner has no products, the brief promotes that URL. *Per new user* is off for such a brief
   until the site can report a sign-up to you.
4. **Every price says its unit.** Each price field ends in `USDC` with its value under it (`= 5 ¢`, `= $5`); one line
   above the prices: *all prices in USDC (1 USDC = $1)*. The brief's card says the same.
5. **Cover picture** in place of *Picture for posts*: the picture that goes with every promoter's post; by default the
   product page's shot, replaced by the first picture the owner drops. Shown 132 × 74, its line wraps.
6. **The link field is full width** (today it is the width of the icon column and shows `https:/`).
7. **Per new user says the rule that counts**: *spends ≥ this on Cymetica in 14 days · a deposit alone never counts*.
   Today the label says *own deposit* and only the tooltip says the fees rule (your *Costs more to fake than it pays*).
8. **Per unique visitor** comes first, then *Per post*, which is priced from it (C).

## C. A post is priced for each promoter (pictures 5, 6, 7, 8)
9. **The owner types no price per post**, only switches posts on (marked *auto*). The post is paid for itself,
   whatever it brings.
10. **On the market the card says *by reach · per post · for your X*** and its button is *See my offer*. In the brief
    the promoter types their X handle and presses *Check my offer*.
11. **What they see**: followers, views a post, real audience, account age, and *Your offer for one post* in large
    type: the visitors you expect from one post × the owner's price per visitor, rounded (to halves under 10 USDC,
    whole USDC to 100, fives above): `~136 visitors × 0.05 = 6.80 → 7 USDC`. Then *Take the offer*. An account you
    refuse sees *Not eligible* and why (picture 8).
12. **Paid once the post has stayed up 7 days** (your rule today). The visitors the post brings count first against
    what the post was paid; above that each is paid at the visitor price, so the owner never pays twice.
13. **The owner approves each offer** (D); the promoter's link arrives on approval.

## D. The brief's own page (`#mybrief/<id>`, pictures 3, 4)
14. **Four numbers**: Spent, Up for grabs, Visitors (unique, 14 days), New users. Not shown: *New visitors* (a second
    count of the same people) and *Posts paid* (the Promoters table says it per promoter).
15. **Offers for a post**, under the numbers: only the promoters waiting for the owner, with followers, views a post,
    real audience, visitors expected and the offer; *Approve* or ✕. *N filtered out by Cymetica*, the reasons on hover.
    An approved one moves to Promoters. It replaces *Quotes from promoters*.
16. **Visitors by day shows the count on hover**: the day, the visitors, the new users (picture 4).
17. **One Promoters table, full width**: promoter, the post (its price and one state: approved, posted, paid),
    visitors, new users, earned, *Pay*. Today's table cuts its last column (*paid* / *Pay*) at the card's edge.
18. **Not shown any more**: *Where they came from*, *Not counted*, *Materials*, and the *N materials* tag on the brief's
    card. Promoters still see the materials inside the brief.
19. **The bell** left of *live · read*: the number of offers waiting across the owner's briefs; it opens the brief
    that has them.

## E. The market (picture 5)
20. **One line above Open briefs**: a shield, *User protection*, a short line, four pills and *How*, which opens the
    fold at the bottom. **Only the place and the look are ours**: the words in the mockup are placeholders; you decide
    what the protection is, write the line, the pills and the fold from it, and secure it.
21. **The loading screen is the one Airdrop Farmer and Company have**: the picture, the percent, one word, the bar.
    Leave out today's row of chips under it (*page · the market · your products · the briefs · your visitors*).
