# Platform policies: can Entry Fees in Stars fund a Prize Pool paid to the winner?

Research for issue #3. Sources checked 2026-10-31. Telegram's pages carry no revision date; Apple's guidelines say "Last Updated: October 16, 2026"; Bot API docs were at 10.3 (August 24, 2026).

## Bottom line

**No. The design as charted (Members pay an Entry Fee in Stars, the pooled Stars go to the winner) is not allowed by the platform rules, and Telegram gives us no way to do it anyway.**

1. **Telegram doesn't support it technically.** Stars only move from a user to a bot (or to a creator or gift). A bot's Star balance can only be spent on Telegram Ads or broadcast fees, or withdrawn by the *developer* as rewards through Fragment. The only way a bot can send Stars back to a user is `refundStarPayment`, which refunds one whole charge to the person who paid it. Bot API has no method that pays Stars out to a user. Gifts a bot sends with `sendGift` "can't be converted to Telegram Stars by the receiver".
2. **Telegram's terms forbid it.** Users may not "transfer or use Stars ... for any other purpose than those explicitly outlined" (Stars ToS §4, §6.1). A bot must not facilitate "regulated or questionable goods and services" (Bot Developer ToS §5.2(h)), and paid-entry contests with prizes are regulated gambling in many places. Bots must also follow Apple's and Google's store rules (Bot Developer ToS §6.2, §9).
3. **Apple and Google forbid it.** On mobile, Stars are bought through Apple and Google in-app purchase. Apple 5.3.3: in-app purchase "may not" buy "credit or currency for use in conjunction with real money gaming of any kind". Google Play bans participating "using real money (including in-app items purchased with money) to obtain a prize of real world monetary value", including apps that "accept or manage wagers, in-app currencies, winnings". Licensed gambling apps must "NOT ... use Google Play In-app Billing", and Stars are always bought that way on Android.
4. **Paying the winner off-platform doesn't fix it.** The developer would withdraw Stars as rewards (TON through Fragment) and pay the winner in crypto or cash. That is real-money gaming with a monetary prize. It needs a gambling licence and geo-restriction in each country (Apple 5.3.4), and the map says the audience is "not restricted by country". It also breaks Apple 5.3.3 at the moment the user pays.

**What is allowed:**
- **Free-to-enter Leagues with prizes the developer funds.** Apple 5.3.1 says contests "must be sponsored by the developer of the app". 5.3.2 requires official rules in the app stating that Apple is not involved.
- **Stars spent on digital goods or services that are not entries into a prize draw:** league creation or hosting, premium stats, cosmetics, and tips to the developer (Apple 3.1.1 allows tipping with in-app currencies).
- **Non-cash bragging rights.** Trophies, badges, standings.

Recommended direction for the map: drop "winner receives the Prize Pool". Either make paid Leagues pay-to-host or pay-for-features with no pooled prize, or make prizes developer-sponsored on free entry. Do neither without a legal opinion on sweepstakes rules in the target countries.

## Telegram

### Terms of Service for Telegram Stars — https://telegram.org/tos/stars

- **§1 Introduction.** Stars "allow users to purchase digital goods and services from bots and mini apps ..., send gifts to content creators ..., and more."
- **§2 / §2.2.** Stars are bought through in-app purchase on iOS and Android, and purchases "may be further subject to the third party's terms" (e.g. Apple in-app purchase).
- **§2.3 Compliance with Local Laws.** Use of Stars "may be subject to additional restrictions in certain jurisdictions ... based on local laws".
- **§4 Balance.** Users may use Stars "to purchase digital goods and services from bots and mini apps, access paid media, donate to content creators or send Telegram gifts. You may not sell, withdraw, transfer or use Stars in your personal balance for any other purpose than those explicitly outlined in these Terms."
- **§5 Abuse.** Telegram may "withhold or permanently debit Stars" for violating "local laws and applicable third-party store terms".
- **§6.1 Using Stars.** "You may not attempt to sell, redistribute, or use Stars for any other purpose than those expressly set out in these Terms."
- The terms don't mention gambling, contests or prizes, and they describe no way for a user to *receive* Stars except as a creator (§6.4) or from paid messages (§6.5).

### Bot Platform Developer Terms — https://telegram.org/tos/bot-developers

- **§5 Code of Conduct.** "Additional local laws and regulations may apply to your TPA. It is your responsibility to ensure that your TPA complies with all applicable legislation".
- **§5.2(h).** "Your TPA must not be used to provide, link to, aggregate, host, index, distribute, lend out, exchange, trade, rent, sell or facilitate the sale of illegal, pirated, regulated or questionable goods and services."
- **§5.2(d).** Bots may not mislead users "into performing certain actions in the pursuit of an unachievable outcome".
- **§6.2 Digital Goods and Services.** Digital goods must be paid "exclusively through the exchange of Telegram Stars". "Telegram must adhere to Apple and Google's definitions of digital goods and services ... you should reference the relevant documentation from Apple and Google directly". A bot that breaks the rules can be made "inaccessible from store versions of Telegram".
- **§6.2.1.** If a bot can't fulfil a purchase, it "is able to return the Stars to the purchaser in full via the relevant Telegram Bot API method". This is the only Stars flow back to users. It supports Cancellation refunds, not payouts.
- **§6.2.2 TPA Balance.** The bot's Stars "do not constitute your property". They "can be used to place Telegram Ads ..., to increase messaging limits ... or to accept rewards" and are "owned by Telegram". Telegram lists no use for paying Stars to other users.
- **§6.2.4 / §6.2.4.1 Rewards.** The developer receives "0.013 USD worth of rewards for each Telegram Star", processed by Fragment. Stars can be withheld or debited for "suspected abuse" or a violation of "applicable third-party store terms".
- **§6.4 Taxes.** The developer is solely responsible for taxes on income.
- **§9 Compliance with Laws.** Bots must "operate within all applicable laws, regulations and third-party Terms of Service (e.g., store guidelines from Apple and Google)".

### Telegram Bot API — https://core.telegram.org/bots/api (10.3)

- `refundStarPayment(user_id, telegram_payment_charge_id)`: "Refunds a successful payment in Telegram Stars". Refunds one specific charge to its payer, in full.
- `sendGift`: "Sends a gift to the given user or channel chat. The gift can't be converted to Telegram Stars by the receiver."
- `getMyStarBalance` / `getStarTransactions`: read-only.
- `transferBusinessAccountStars`: moves Stars from a connected *business account* into the bot's balance. It goes toward the bot, not out to users.
- No method sends Stars from a bot to a user.

### Mini Apps user terms — https://telegram.org/tos/mini-apps

They cover users connecting to third-party providers and contain nothing on gambling, contests or prizes. The developer-side rules above govern.

### Telegram ToS §7.8 Giveaways in Channels — https://telegram.org/tos

Telegram's own giveaways are funded by the admin ("at their expense"), not by entry fees. "Certain countries or jurisdictions may impose regulatory constraints on giveaways. If you run a giveaway, you are solely responsible for complying with applicable law." This supports the developer-sponsored model, not a pooled one.

## Apple App Store Review Guidelines — https://developer.apple.com/app-store/review/guidelines/ (Last Updated October 16, 2026)

Telegram for iOS is the host app. Under **4.7** it is "responsible for all such software offered in your app [HTML5 mini apps, chatbots], including ensuring that such software complies with these Guidelines". **4.7.1** requires that mini apps "follow Guideline 3.1 in order to offer digital goods or services". Telegram therefore has to enforce these rules against our Mini App.

- **3.1.1 In-App Purchase.** In-app currencies may be used to "'tip' the developer or digital content providers". Gifts of in-app purchase items "may only be refunded to the original purchaser and may not be exchanged."
- **5.3 Gaming, Gambling, and Lotteries.** "one of the most regulated offerings on the App Store."
  - **5.3.1** "Sweepstakes and contests must be sponsored by the developer of the app." A pool funded by the Members' Entry Fees is not developer-sponsored.
  - **5.3.2** "Official rules for sweepstakes, contests, and raffles must be presented in the app and make clear that Apple is not a sponsor".
  - **5.3.3** "Apps may not use in-app purchase to purchase credit or currency for use in conjunction with real money gaming of any kind." Stars bought on iOS are exactly that, so this clause rules out a Stars Prize Pool.
  - **5.3.4** Real money gaming "(such as sports betting ...)" needs "necessary licensing and permissions in the locations where the app is used, must be geo-restricted ... and must be free on the App Store."
- **5.1.1(ix).** Gambling apps "should be submitted by a legal entity that provides the services".

## Google Play — Real-Money Gambling, Games, and Contests — https://support.google.com/googleplay/android-developer/answer/9877032

- Licensed gambling and daily fantasy sports apps must be free and "NOT ... use Google Play In-app Billing". Stars bought in Telegram for Android go through Play Billing.
- **Other Real-Money Games, Contests, and Tournament Apps.** "we don't allow content or services that enable or facilitate users' ability to wager, stake, or participate using real money (including in-app items purchased with money) to obtain a prize of real world monetary value." The listed violations include "Games that accept money in exchange for an opportunity to win a physical or monetary prize", calls to action to "COMPETE! in a tournament for a chance to win a cash prize", and "Apps that accept or manage wagers, in-app currencies, winnings, or deposits in order to gamble for, or obtain a physical or monetary prize."
- **Gamified Loyalty Programs.** In-game points "may not be wagered, awarded or exponentiated by game performance or chance-based outcomes", and "no portion of the qualifying monetary transaction may represent a fee or wager to participate".

Could a Prize Pool be argued to have no "real world monetary value"? Stars have a published reward value (0.013 USD each, Bot Developer ToS §6.2.4), and the only way to pass the pool to a winner is to cash it out. The argument fails.

## Enforcement precedents (secondary sources; not verified against a primary source)

- Trade press reports that Telegram blocked the casino Mini App "TG.Casino". Users saw a notice that the bot couldn't be displayed in the Google Play version of Telegram ([SiGMA](https://sigma.world/news/telegram-shuts-down-tg-casino-over-policy-violations/); the page returned 403 when fetched). This matches the mechanism in Bot Developer ToS §6.2: removal "from store versions of Telegram".
- 2026: governments pressured Telegram over gambling content. The Philippines threatened a ban, and Telegram agreed to crack down ([Vixio](https://www.vixio.com/blog/latest-gambling-news-telegram-averts-philippines-ban-targets-gambling-content-and-more)). Russia warned it would restrict Telegram over casino and betting groups ([CasinoBeats](https://casinobeats.com/2026/01/26/shut-down-russian-casinos-or-face-restrictions-moscow-warns-telegram/)).

## Open questions (out of scope here)

- Whether a *skill-based* prediction contest with paid entry counts as gambling under the laws of specific countries (it varies; e.g. some US states treat paid-entry skill contests differently). This only matters if the app moves off Stars and app-store billing entirely, and that needs a lawyer.
- Whether developer-sponsored prizes (e.g. Premium gifts through `giftPremiumSubscription`) on free Leagues need sweepstakes registration in particular countries.
