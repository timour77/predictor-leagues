# Paid prediction Leagues among friends: how gambling and pool-betting law treats them

Resolves issue #4. Researched 2026-10-31. **This is not legal advice.** Below are primary-source readings by a non-lawyer. Get counsel in each target market before launch.

## Bottom line

In the UK, Germany/France (EU), Russia and most US states, a League where players **pay an Entry Fee in something of value** and the **best predictor takes a Prize Pool made of those fees** is treated as **betting, specifically pool betting**. It is not a lawful skill contest. Being a skill game does not save it:

- **UK:** the statute says outright that predicting "using skill or judgment" in a paid prize competition counts as betting, and a prize funded by stakes is pool betting.
- **Germany:** paid wagers on future events are gambling "in jedem Fall" (in every case).
- **US federal (UIGEA):** the fantasy carve-out requires that prizes are **not** determined by the number of entrants or the fees paid. A pooled pot fails that test by design.

**"Private among friends" protects the *players*, not *us*.** The exemptions that exist (UK domestic/workers' betting, German "closed circle", Texas-style social-gambling defences, Russian non-enforceability of private wagers) cover people betting with each other, mostly not in the course of a business. A public Telegram Mini App that collects fees and distributes pools is almost certainly the **organiser/operator** "in the course of a business", whether or not it takes commission. Taking a commission makes this clearer and worse. Taking none does not make the app safe.

**Telegram Stars do not get us out.** Stars carry a monetary value Telegram assigns and pays developers for (see the Telegram section below). Regulators look at "money or money's worth", not at the currency label. Stars Terms also forbid using Stars for anything outside the listed purposes and let Telegram debit Stars for breaches of local law.

**Practical conclusion:** as currently specified (paid entry, pooled prize, borderless audience), the product is unlicensed pool betting in the UK, gambling the EU states examined prohibit or reserve, and prohibited internet gambling in Russia. Lower-risk shapes are discussed in Safeguards. The strongest of them is to **break the link between fees and prizes**: free entry, or a fee for the service with fixed, sponsor- or house-funded prizes, or no prizes of value.

Confidence: **high** for the UK and Germany (statute text is explicit). **Medium-high** for Russia (statute is explicit about organisers, but whether Stars count as a "stake" in money is untested). **Medium** for the US (fifty different state regimes) and for the rest of the EU/CIS (not individually researched).

## Per-jurisdiction table

| Jurisdiction | How a paid friends' prediction League with a pooled prize is classed | Private/social exemption? | Does it cover the app as operator? | Key sources |
|---|---|---|---|---|
| **UK (GB)** | Betting under s.11 (prize competition: pay to participate, guess a sporting outcome, more accurate guess wins). "Guessing" expressly includes "predicting using skill or judgment" (s.11(2)). Pool betting under s.12 when winnings depend on the aggregate of stakes or are divided among winners. Needs a Gambling Commission remote pool betting licence. | Yes, narrow: "private betting" = domestic betting (all parties live on the same premises) or workers' betting (same employer), Sch.15 paras 6-8. Also s.296(3): no offence when acting "otherwise than in the course of a business". | **No.** The UKGC's fantasy-football guidance says a licence may be needed when prize values depend on the number of paying entrants, and that promoting a league via social media/advertising may mean it is run "in the course of a business". | [GA 2005 s.11](https://www.legislation.gov.uk/ukpga/2005/19/section/11), [s.12](https://www.legislation.gov.uk/ukpga/2005/19/section/12), [s.296](https://www.legislation.gov.uk/ukpga/2005/19/section/296), [Sch.15](https://www.legislation.gov.uk/ukpga/2005/19/schedule/15), [UKGC guidance (2017, upd. 2021)](https://www.gamblingcommission.gov.uk/news/article/gambling-commission-warns-fantasy-football-organisers-to-not-get-caught-out) |
| **Germany (EU)** | Gambling (Glücksspiel) under §3(1) GlüStV 2021: paying for a chance to win where the outcome depends wholly or predominantly on chance. The outcome "in jedem Fall" depends on chance when it turns on uncertain future events, and "Wetten gegen Entgelt auf den Eintritt oder Ausgang eines zukünftigen Ereignisses sind Glücksspiele". Licensable *Sportwetten* are only **fixed-odds** bets, so a pari-mutuel pool cannot get a sports-betting licence. | Only non-public games are outside scope. "Public" = open to a larger, non-closed group, or habitually run in clubs/closed societies (§3(2)). | **No.** An app anyone can join is open to a non-closed group. Recurring leagues are also "habitual". | [GlüStV 2021 §3](https://www.gesetze-bayern.de/Content/Document/StVGlueStV2021-3) |
| **France (EU)** | Jeux d'argent et de hasard are prohibited in principle (CSI art. L.320-1), with only listed exceptions (L.320-6: licensed ANJ operators, FDJ/PMU). The test: public offer, hope of gain, financial sacrifice, and chance "même partiellement". The ban extends to games resting on players' savoir-faire. | No public offer = outside the test. | **No.** A public app is a public offer. | [L.320-1 commentary (CPO, Assemblée nationale)](https://www.actu-juridique.fr/fiscalite/fiscal-finances/vers-une-taxation-des-jeux-dargent-et-de-hasard/), [AN amendment text](https://www.assemblee-nationale.fr/14/amendements/1156/AN/960.pdf) (the Légifrance article was not retrieved; see Open questions) |
| **Other EU states** | Not individually researched. Most follow a similar "stake + prize + (partial) chance" test with state monopolies or licences. Assume the German/French position until checked. | Varies | Assume no | — |
| **Russia** | 244-FZ art.4: азартная игра = "основанное на риске соглашение о выигрыше"; пари = such an agreement whose outcome depends on an uncertain event; выигрыш = money **or other property, including property rights**. Art.5(3): organising gambling via the internet/telecom networks is **prohibited**, except interactive bets taken by licensed bookmakers/totes through the ЕЦУПС (art.14.2). Art.6(1): organisers may only be Russian-registered legal entities. Penalties: КоАП 14.1.1; УК 171.2 (criminal, incl. internet). | Private wagers between individuals are not criminalised, but are unenforceable (ГК 1062(1)). | **No.** The app that takes Entry Fees and pays out pools is the "организатор". Untested edge: art.4(3) defines a ставка as "денежные средства", and whether Stars are "money" is unclear. But winnings as "иное имущество / имущественные права" plus the real-money value of Stars make an "it's not money" defence risky. | [244-FZ text](https://legalacts.ru/doc/federalnyi-zakon-ot-29122006-n-244-fz-o/), [ГК 1062](https://www.zakonrf.info/gk/1062/), [КоАП 14.1.1 / УК 171.2 overview](https://www.consultant.ru/law/podborki/azartnye_igry_v_seti_internet/) |
| **CIS (KZ, BY, UZ, etc.)** | Not researched. Most derive from the same Soviet/Russian model and license or prohibit online betting. Assume prohibited unless licensed. | Varies | Assume no | — |
| **US: federal** | UIGEA (31 U.S.C. §5362(1)) excludes fantasy/simulation contests only if (a) prizes are fixed and announced in advance **and not determined by the number of participants or fees paid**, (b) outcomes reflect skill and are determined predominantly by accumulated statistics of individual athletes across multiple events, and (c) no outcome rests on a single team's score/point spread or one athlete in one event. Predicting match results with a pooled pot fails (a) and (c). UIGEA also defers to state law; it legalises nothing. | n/a | n/a | [31 U.S.C. §5362](https://www.law.cornell.edu/uscode/text/31/5362) |
| **US: states** | State law governs. Typical "social gambling" defences, e.g. Texas Penal Code §47.02(b), require a **private place**, that **no person received any economic benefit other than personal winnings**, and equal odds apart from skill/luck. Some states treat even paid DFS as illegal gambling (Washington's Gambling Commission said so publicly; DFS operators geo-block WA). Paid "pick'em" on game results is generally regulated as sports betting where legal. | Yes in many states, for friends betting among themselves | **Unlikely.** An app is not a "private place", and an operator taking any fee is an "economic benefit". Even with zero commission, the operator is facilitating unlicensed pool wagering. | [Tex. Penal §47.02](https://texas.public.law/statutes/tex._penal_code_section_47.02), [Perkins Coie on WA (2015)](https://www.perkinscoie.com/en/news-insights/no-game-changer-for-fantasy-sports-in-washington.html) |

### Telegram platform layer

- Bot Developer ToS §6.2: digital goods/services must be paid "exclusively through the exchange of Telegram Stars". §6.2.1: bots can refund Stars in full ([Bot Dev ToS](https://telegram.org/tos/bot-developers)).
- Stars ToS §4/§6.1: Stars may not be sold, withdrawn, transferred or used "for any other purpose" than those listed. §2.3: local law may restrict using Stars. §5: Telegram may debit Stars for violating the Terms or local law ([Stars ToS](https://telegram.org/tos/stars)).
- Developers can "accept a reward for the monetary value that Telegram assigns to each Star" ([Bot payments docs](https://core.telegram.org/bots/payments-stars)). This is why Stars are "money's worth" for gambling-law purposes.
- Neither ToS document has an explicit gambling clause, and **no documented mechanism lets a bot pay arbitrary Stars to a winning user** (only refunds, gifts and similar). Paying out a Prize Pool in Stars may be technically impossible or a ToS breach, separately from gambling law. Telegram has removed gambling bots in practice (e.g. press reports on TG.Casino; secondary source).

## Factors that flip the classification

| Factor | Pushes toward gambling/pool betting | Pushes toward lawful contest |
|---|---|---|
| **Consideration** (paying to enter) | Any Entry Fee in money or money's worth (Stars included) | Genuinely free entry, with any paid tier giving no better chance of a prize |
| **Prize source** | Prize = sum of entry fees ("aggregate of stakes", UK s.12; "determined by number of participants or fees", UIGEA) | Fixed prize funded by the operator/sponsor, announced in advance, independent of entrant count |
| **Prize value** | Money, Stars, anything convertible | Non-transferable bragging rights, badges, cosmetic items with no cash-out |
| **Skill vs chance** | Weak defence for match-result prediction: UK s.11(2) treats skill/judgment predictions as betting; DE says future-event wagers always depend on chance; UIGEA excludes single-game outcomes | Matters only in "predominance" jurisdictions (some US states, DE outside wagers), and mainly for multi-event, stat-based fantasy formats |
| **Operator commission (rake)** | Makes the operator clearly "in the course of a business" and gives it an economic benefit (Texas test) | Zero rake helps players' social-gambling defence but does **not** stop the app being the organiser |
| **Private vs public** | Open sign-up, invite links that spread, advertising, social promotion (UKGC), habitual/recurring leagues (DE §3(2)) | Truly closed groups run by the players themselves, with no third-party platform holding funds |
| **Who holds the money** | Platform collects and distributes (custody = organiser) | Players settle among themselves off-platform. This shifts risk to the users and is still illegal in some places. The app should not facilitate it either. |
| **Audience location** | UK/EU/RU/most US states | Few places with a clear safe harbour for pooled paid prediction |

## Safeguards (ranked by how much risk they actually remove)

1. **Decouple fees from prizes (most effective).** Options:
   - (a) Free-to-play Leagues with no prize of value.
   - (b) Paid *service* features (premium stats, custom league themes) that never affect who wins anything.
   - (c) Prizes funded by us/sponsors, fixed in advance, with free entry or a free alternative method of entry (this then becomes a prize-competition/promotion question, not betting).
2. **No custody of pools and no Stars payouts to winners.** Avoids being the "organiser" and avoids the Telegram ToS problem.
3. **If paid pooled Leagues remain:** a licence is the only clean route (e.g. a UKGC remote pool betting licence, or a Curaçao/Malta-type B2C licence plus geo-blocking of everywhere else). That means a regulated business: KYC/AML, responsible gambling, age verification, taxes.
4. **Geo-blocking** of at least RU, UK, US, FR, DE and other EU states. This reduces but does not remove exposure. Telegram gives no reliable user location (phone-number country code is a weak signal), so blocking will be leaky. Russia's ban targets internet organisation regardless of where the operator sits.
5. **18+ age gate.** Required everywhere gambling is permitted. It does not change the classification.
6. **Zero commission.** Necessary but not sufficient. It removes the most obvious "business" indicator but does not make a public platform "private betting".
7. **Closed, invite-only Leagues with a member cap.** Weak mitigation. It helps the "non-closed circle" argument in DE only marginally, and does nothing under UK s.11/s.12 once run in the course of a business.

## Open questions / uncertainty

- France: the Légifrance text of CSI L.320-1 / L.320-6 was not retrieved directly (404). The definition is taken from parliamentary and CPO material quoting it.
- Russia: whether Telegram Stars count as "денежные средства" for a ставка is untested. Exact current КоАП 14.1.1 / УК 171.2 sanctions were not confirmed.
- US: only federal UIGEA and the Texas/Washington examples were checked. State-by-state review is needed if the US is a target.
- Telegram: whether any Bot API method lets a bot transfer Stars to arbitrary users as a prize, and whether Telegram's ToS for Content Creators/developers contains gambling restrictions not found here.
- Not researched: Ukraine, Kazakhstan, Belarus, Uzbekistan, Georgia, Armenia, Israel, Cyprus/Malta-specific regimes.
