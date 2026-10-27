# Promo Market v3: changes on top of v2 (ET-32929)

Draft, not filed. The look is THEIR live page with these changes on it: `python outbox/promo-market-v3/live/serve.py`,
then http://127.0.0.1:8792/expire76#new (the owner), /expire76#mybrief/9001 (a brief's own page) and /promo-market (a
stranger). The switch at the bottom left (or `?v2`) shows the same page as v2 draws it today. Pictures:
`python outbox/promo-market-v3/live/render.py` → `pictures/` (not in git; made again in a minute).

There is no live brief yet, so the copy serves one sample brief (Gem Screener, 100 USDC, five promoters, handles ending
`_demo`) to both versions, from one model (`live/sample.py`). Every figure about it is invented.

Asked by the operator on 2026-10-27. Everything below is a patch on v2; what is not named stays as it is.

**We give only the look. The look of the mockup is binding; how it works is yours**: how reach is measured, how fakes
are caught, what a check says, and every word the page shows about protection is for you to write and secure. Where
your backend cannot do what is drawn, change the design as little as it takes and name each change in your BB-SPEC.

## A. The product's own address, and its maker
1. **`cymetica.com/promo-market`** opens the market (the Market tab) for anybody, signed in or not. It is the product's
   address. `/creator-dashboard` (the link in the daily Telegram post) keeps opening a member's dashboard as today.
2. **The Universe says *Made by BJ Ironstar Capital*** on the Promo Market building and its panel (today: Cymetica).

## B. Post a brief (`#new`)
3. **Any website, not only an app on Cymetica.** First tile of the picker: *My own website* → a name and a URL. Picked
   (or when the owner has no products), the brief promotes that URL; the POST carries `url` and `name` in place of
   `product_path`. *Per new user* is off for such a brief until the site carries Cymetica's sign-up tag.
4. **Every price says its unit.** Each price field ends in `USDC`, with its value under it (`= 5 ¢`, `= $5`). One line
   above the prices: *all prices in USDC (1 USDC = $1)*. The brief card says the same.
5. **Cover picture** in place of *Picture for posts*: the picture that goes with every promoter's post; by default a
   screenshot of the product page, replaced by the first picture the owner drops.
6. **The link field is full width** (today it is the width of the icon column: `https:/`).
7. **Per new user says the rule that counts**: *spends ≥ this on Cymetica in 14 days · a deposit alone never counts*.
   Today the label says *own deposit* and only the tooltip says the fees rule (your `/api/v1/promo/how-counted`, *Costs
   more to fake than it pays*). The same text in the brief's drawer.
8. **Per unique visitor** comes first, then *Per post*, which is priced from it (C).

## C. A post is priced for each promoter
9. **The owner sets no price per post**, only whether posts are paid (a switch, marked *auto*). The post is paid for
   itself, whatever it brings: the promoter's money for posting.
10. **The promoter gives their X handle** in the brief (*See my offer* on the card, then *Check my offer*). Your
    verification layer reads the account: real views of the last 20 posts, how much of the audience is real, its age;
    and estimates the unique visitors one post will bring.
11. **The offer = expected visitors × the owner's price per visitor, rounded**: to halves under 10 USDC, whole USDC to
    100, fives above. `~136 visitors × 0.05 = 6.80 → 7 USDC`. A bought audience, a new account, or one device or wallet
    behind two promoters gets *Not eligible* and the reason instead.
12. **Paid once the post has stayed up 7 days** (your rule today). The visitors the post brings are first counted
    against what the post was paid; above that each is paid at the visitor price, so the owner never pays twice.
13. **The owner approves each offer** (D). The promoter's link arrives on approval.

## D. The brief's own page (`#mybrief/<id>`), trimmed
14. **Four numbers**: Spent, Up for grabs, Visitors (unique, 14 days), New users. Gone: *New visitors* (a second count
    of visitors, the paid ones; the owner needs one) and *Posts paid* (the Promoters table says it per promoter).
15. **Offers for a post**, right under the numbers: only the promoters waiting for the owner, with followers, views a
    post, real audience, visitors expected and the offer; *Approve* or ✕. *N filtered out by Cymetica*, the reasons on
    hover. An approved one moves to Promoters. It replaces v2's *Quotes from promoters*.
16. **Visitors by day shows the count on hover** (the day, the visitors, the new users); v2's chart shows none.
17. **One Promoters table, full width**: promoter, the post (its price and one state: approved, posted, paid), visitors,
    new users, earned, *Pay*. v2's table cut its last column (*paid* / *Pay*) at the card's edge at 2000 px, and its
    paid state repeated the one in the offers list; there is one list now.
18. **Gone as noise**: *Where they came from*, *Not counted*, *Materials* (the owner sees what they uploaded in Post a
    brief; promoters still see the materials in the brief), and the *N materials* tag on the brief's card.
19. **The bell** in the top bar counts the offers waiting across the owner's briefs and opens the brief that has them.

## E. User protection on the market
20. **One line above Open briefs**: a shield, *User protection*, a short line, four pills and *How*, which opens the
    fold at the bottom that lists the rules. **Only the place and the look are ours.** The wording of the line and the
    pills in the mockup is a placeholder: you decide what the protection is, write the pills and the fold from it, and
    secure it as you see fit.
21. **The loading screen is the one Airdrop Farmer and Company have**: the picture, the percent, one word, the bar.
    v2 adds a row of chips (*page · the market · your products …*) under it; leave it out.
