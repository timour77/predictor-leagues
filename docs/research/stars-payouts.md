# How can a bot pay out Telegram Stars to a user?

Research for issue #2. Checked against primary sources on 2026-10-31. The latest Bot API at that date is **10.3 (Aug 24, 2026)**.

## Bottom line

**A bot cannot send Stars to a user. No Bot API method does this, including in 10.3.** A bot's Star balance can leave the bot in only these ways:

1. As a **refund** of one specific payment, back to the user who made it (`refundStarPayment`).
2. As **spending on Telegram products** for a user: gifts (`sendGift`, `giftPremiumSubscription`), paid broadcasts and ads.
3. As a **withdrawal by the bot owner** through Fragment, paid in crypto (TON) at 0.013 USD per Star. Stars can be held for up to 21 days first.

So "winner receives the Prize Pool in Stars" can't be built as stated. The workable options:

- **(A) Off-platform cash payout.** The owner withdraws via Fragment and pays the winner in TON. This costs about 35% versus the 0.02 USD ad value per Star, is delayed up to 21 days, and carries ToS and regulatory risk.
- **(B) In-kind prizes.** The bot spends the pool on Telegram Gifts or Premium for the winner. The value is real but can't be withdrawn: Telegram says bot-sent gifts can't be converted to Stars. The one exception is upgraded collectible gifts, which the winner can resell.
- **(C) Price the League in TON instead of Stars.** Developer Terms §7 allows crypto in Mini Apps, but only on TON. Real peer-to-peer value transfer is possible there, with its own legal questions.
- **(D) Refund-based flows only for cancelled Leagues.** `refundStarPayment` returns each entrant's own fee. It cannot route money to the winner.

The real blocker is policy as much as API. Telegram's terms say Stars on your balance "do not constitute your property". They also forbid redistributing Stars for purposes the terms don't list. Paid entry fees with a prize pool also look like the "regulated or questionable goods and services" that §5.2(h) of the Developer Terms prohibits. Get a ToS and legal read before shipping any of A to C.

## Mechanisms in detail

### 1. Direct Star transfer bot to user: does not exist

- The Bot API index has no method that credits Stars to a user's balance. ([Bot API](https://core.telegram.org/bots/api))
- `TransactionPartnerUser.transaction_type` lists every kind of bot-to-user Star movement. The values are `invoice_payment`, `paid_media_payment`, `gift_purchase`, `premium_purchase` and `business_account_transfer`. None of them is a payout. ([Bot API: TransactionPartnerUser](https://core.telegram.org/bots/api#transactionpartneruser))
- The changelog from Bot API 7.4 (May 2024, when Stars launched) to 10.3 (Aug 2026) adds no payout or transfer method. All of the 2026 releases, 9.4 to 10.3, only touch gift metadata (`UniqueGiftInfo`, `rarity`, `is_burned`). ([Bot API changelog](https://core.telegram.org/bots/api-changelog))
- `transferBusinessAccountStars` (9.0) goes the other way. It moves Stars **from** a managed business account **to** the bot, 1 to 10000 per call, and needs the `can_transfer_stars` right. ([Bot API](https://core.telegram.org/bots/api#transferbusinessaccountstars))
- MTProto (the client API) also has no general peer-to-peer Star transfer. The only balance-to-balance move it documents is "business account → business bot". ([Telegram Stars, client API](https://core.telegram.org/api/stars))

### 2. `refundStarPayment`

- Parameters are `user_id` and `telegram_payment_charge_id`. It refunds one successful Stars payment in full, to the original payer only. ([Bot API](https://core.telegram.org/bots/api#refundstarpayment))
- Developer Terms §6.2.1 says the bot returns the Stars, and refunds are deducted from the bot's balance. ([Bot Developer Terms](https://telegram.org/tos/bot-developers))
- **For Leagues:** this is useful to cancel a League or return entry fees. It can't pay the winner more than they paid in.

### 3. `sendGift` (paid gifts, since 8.0)

- It sends a gift from `getAvailableGifts`, paid from the bot's balance, to a user or channel. The docs say: "The gift can't be converted to Telegram Stars by the receiver." ([Bot API](https://core.telegram.org/bots/api#sendgift))
- `pay_for_upgrade=true` also pays the upgrade to a **unique (collectible) gift** from the bot's balance. ([Bot API](https://core.telegram.org/bots/api#sendgift))
- The winner can list a unique gift on Telegram's marketplace for Stars or TON. ([Telegram Gifts](https://core.telegram.org/api/gifts))
  - Price limits come from the `stars_/ton_stargift_resale_amount_min/max` config values.
  - The seller gets `price × *_resale_commission_permille / 1000`.
  - The gift may be locked until `can_resell_at`.
  - It can also be exported as a TON NFT via `payments.getStarGiftWithdrawalUrl`.
- **For Leagues:** this is the only route from bot Stars to anything a user can trade. It loses value and depends on market prices, and buying collectibles to pass on cash value may break the "no redistribution" terms. Not recommended as the main payout.

### 4. `giftPremiumSubscription` (since 9.0)

- It gifts Premium paid from the bot's balance. The price is fixed: 3, 6 or 12 months for **1000, 1500 or 2500 Stars**. ([Bot API](https://core.telegram.org/bots/api#giftpremiumsubscription))
- **For Leagues:** a clean, allowed in-kind prize. It only fits pools that match those amounts, and the winner gets no cash value.

### 5. Owner withdrawal via Fragment (TON)

- Rate: "Developers can receive an equivalent of 0.013 USD worth of rewards for each Telegram Star." For comparison, ad credit is worth 0.02 USD per Star. ([Bot Developer Terms §6.2.3 and §6.2.4](https://telegram.org/tos/bot-developers))
- Holding: Stars "may not become available for advertising credits or rewards for up to 21 days after their receipt". Telegram can also withhold or debit Stars for refunds or suspected abuse. ([Bot Developer Terms §6.2.4](https://telegram.org/tos/bot-developers))
- Mechanics:
  - The owner calls `payments.getStarsRevenueWithdrawalUrl` (client API, needs 2FA) and gets a Fragment page to enter a TON wallet.
  - The balance must be at least `stars_revenue_withdrawal_min`, and `withdrawal_enabled` must be set. These are client config values, so read them rather than hard-coding.
  - Each withdrawal is capped at `stars_revenue_withdrawal_max`.
  - ([Telegram Stars: Withdrawing revenue](https://core.telegram.org/api/stars), [payments.getStarsRevenueWithdrawalUrl](https://core.telegram.org/method/payments.getStarsRevenueWithdrawalUrl))
- Fragment may refuse some users or countries. Fragment also picks the payout crypto. ([Bot Developer Terms §6.2.4.1](https://telegram.org/tos/bot-developers), [Fragment Terms](https://fragment.com/terms))
- Bots can track withdrawals through `getStarTransactions` with `TransactionPartnerFragment` and `RevenueWithdrawalState`. ([Bot API](https://core.telegram.org/bots/api#transactionpartnerfragment))
- **For Leagues:** this is the only way to turn the pool into withdrawable value. The money passes through the developer, so the developer then pays the winner off-platform. This is a manual or semi-automated TON payout with custody, tax (§6.4) and gambling-law exposure.

### 6. Other balance outflows (not payouts)

- Paid broadcasts cost 0.1 Stars per message above 30 msg/s. Enabling them needs at least 100,000 Stars on the balance and 100,000 MAU. ([Developer Terms §6.2.5](https://telegram.org/tos/bot-developers))
- Telegram Ads can be paid at 0.02 USD per Star. ([Developer Terms §6.2.3](https://telegram.org/tos/bot-developers))
- Stars expire 3 years after receipt (§6.2.7).

### 7. Things that look like payouts but aren't available to bots

- **Star giveaways:** `prize_star_count` puts real Stars into winners' balances. Channels run them through the client app. The Bot API only **reports** them (`Giveaway`, `GiveawayWinners`) and has no method to create one. ([Bot API: Giveaway](https://core.telegram.org/bots/api#giveaway), [Stars: Star giveaways](https://core.telegram.org/api/stars))
- **Gifting Stars user to user:** this goes through a new store or invoice purchase (`inputStorePaymentStarsGift`), not a spend from an existing balance, and it isn't in the Bot API. ([Telegram Stars: Buying or gifting stars](https://core.telegram.org/api/stars))
- **Stars ToS for users** (§4): "You may not sell, withdraw, transfer or use Stars in your personal balance for any other purpose than those explicitly outlined". Even if the winner got Stars, they couldn't cash them out unless they're a creator or developer under separate terms. ([Telegram Stars Terms](https://telegram.org/tos/stars))

## Policy notes relevant to paid Leagues

- §6.2.2: Stars on the developer balance "do not constitute your property". ([Developer Terms](https://telegram.org/tos/bot-developers))
- Stars ToS §6.1: users may not "sell, redistribute, or use Stars for any other purpose than those expressly set out". ([Stars Terms](https://telegram.org/tos/stars))
- §5.2(h): a TPA may not facilitate "illegal, pirated, regulated or questionable goods and services". The terms never name gambling or contests. A pooled entry-fee prize is a regulated game of chance or skill in many places. ([Developer Terms](https://telegram.org/tos/bot-developers))
- §7: crypto features in Mini Apps must use TON. This is what makes option (C) a sanctioned route for real-value pools. ([Developer Terms](https://telegram.org/tos/bot-developers))

## Open questions / not verified

- The current value of `stars_revenue_withdrawal_min`. An unofficial client translation string suggests 1000 Stars, but that's unconfirmed, so read it from config.
- The current resale commission (`stars_stargift_resale_commission_permille`) and `stargifts_convert_period_max`. These are live config values that the docs don't publish.
- Whether Telegram enforces anything against prize-pool bots in practice. Neither the terms nor the docs address it directly.
