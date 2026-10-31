# Is football-data.org adequate as the match data source?

Research for issue #5. Sources checked 2026-10-31.

## Bottom line

**Yes, keep football-data.org for launch. Plan to move to the €12/month "Free w/ Livescores" tier once Leagues are live.** Switching providers is not worth it.

- **Coverage fits.** The free tier covers the 12 Competitions a European prediction app needs: the top 5 leagues, the Champions League, the Eredivisie, Primeira Liga, Championship, Brasileirão, the World Cup and the Euros.
- **Rate limit is fine.** 10 calls/min is plenty for our access pattern: one call per Competition, with a 5-minute in-process cache in `football_api.py`.
- **The real limits are delay and terms:**
  - The free tier serves **delayed** scores and the provider publishes no delay figure, so FINISHED can show up late. That only postpones scoring. It does not make scores wrong, because predictions lock at kickoff.
  - The terms **require a visible attribution line**. They also say **team crests are copyrighted by their owners**, and we display those crests today.
  - The terms give **no uptime or accuracy guarantee**. They do not ban commercial use. A paid plan is still a reasonable step once we charge Telegram Stars for paid Leagues.
- **API-Football** is the cheapest upgrade if we ever need more Competitions or faster status: $19/month for 7,500 requests/day, with a documented 15-second fixture refresh. Its **free tier cannot serve the current season**, so it is no option for a free launch.
- **Sportmonks** is the most expensive per Competition and has the weakest free tier. It does not suit this app.

## How the app uses it today

`backend/app/services/football_api.py` calls football-data.org v4 with `X-Auth-Token`:

- `/competitions/{id}/matches` with `dateFrom`, `dateTo` and `status` filters
- `/matches` for today's matches
- `/competitions`

Responses are cached in memory for 300 s. The service maps `status`, `score.fullTime`, team names and **crest URLs**. `routers/predictions.py` awards points only when `match_results.status == "FINISHED"`. Nothing handles POSTPONED, CANCELLED or AWARDED yet.

## football-data.org in detail

### Plans

Source: [pricing page](https://www.football-data.org/pricing).

| Plan | €/month | Calls/min | Competitions | Scores |
|---|---|---|---|---|
| Free | 0 | 10 | 12 | Delayed |
| Free w/ Livescores | 12 | 20 | 12 | Live |
| Free + Deep Data | 29 | 30 | 12 | Live |
| Standard | 49 | 60 | 30 | Live |
| Advanced | 99 | 100 | 50 | Live |
| Pro | 199 | 120 | 100 | Live |

- The [v4 policies doc](https://docs.football-data.org/general/v4/policies.html) still says Standard gets 30 calls/min. The pricing page says 60. Treat the pricing page as current.
- Unauthenticated clients get 100 requests per 24 h, and only for the area and competition list endpoints.

### Free Competitions

Source: [coverage page](https://www.football-data.org/coverage).

The free tier covers these 12 Competitions:

- Champions League
- Premier League
- Championship
- Bundesliga
- Serie A
- La Liga
- Ligue 1
- Eredivisie
- Primeira Liga
- Brasileirão Série A
- FIFA World Cup
- European Championship

### Status and latency

Source: [v4 Match docs](https://docs.football-data.org/general/v4/match.html).

- **Status values:** SCHEDULED, TIMED, IN_PLAY, PAUSED, FINISHED, SUSPENDED, POSTPONED, CANCELLED, AWARDED. `LIVE` is a filter, not a status.
- **When FINISHED is set:** the docs say "the final whistle pushes the match to FINISHED."
- **Delay length:** no page gives a number for the free-tier delay, or for how fast POSTPONED or AWARDED changes appear. The pricing page only labels free scores as "Delayed" and paid scores as "Live".
- **What to do:** poll every few minutes after expected full time and re-check until FINISHED. Do not assume the status changes immediately.
- **Unverified:** v4 seems to report extra time and penalties separately from regular time in `score`. We read `score.fullTime`, so for knockout ties check what it contains before scoring cup matches.

### Terms

Source: terms on the [about page](https://www.football-data.org/about) and [register page](https://www.football-data.org/client/register), last updated 2018-06-01.

- **No commercial-use ban.** The founder describes the project as "a small side business".
- **Attribution (§7.1):** the app must show "Football data provided by the Football-Data.org API" in a visible place. We do not show it yet.
- **One application per key (§2.3).**
- **Keys must not be committed to open-source repos (§6.1).**
- **Fair use (§3.3):** the provider can cancel an account for excessive usage without notice.
- **Crests and photos (§9.2):** logos and player photos are copyrighted by their owners and need the owners' consent. We currently show crest URLs from the API.
- **After cancellation (§9.1):** we may no longer reference the data.
- **No warranty** of accuracy or availability.
- **Price changes** need 30 days' email notice.

## Alternatives

### API-Football (api-sports.io)

Its site is behind a Cloudflare bot check that blocked direct fetching. The figures below come from search-indexed text of the official pages: [pricing](https://www.api-football.com/pricing), [documentation](https://www.api-football.com/documentation-beta), [terms](https://www.api-football.com/terms) and the [beginner's guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide).

**Plans:**

| Plan | $/month | Requests/day |
|---|---|---|
| Free | 0 | 100 |
| Pro | 19 | 7,500 |
| Ultra | 29 | 75,000 |
| Mega | 39 | 150,000 |

- The official pricing page shows Mega inconsistently, so confirm its price before relying on it.
- Quotas reset at 00:00 UTC.
- The free plan also has a per-minute limit of about 10 requests.

**Other findings:**

- **Free tier seasons:** limited to older seasons. A [vendor tutorial](https://www.api-football.com/news/post/how-to-get-all-data-from-a-league-with-api-football) says the free window is Year-4 to Year-2, with no current season. That rules the free tier out for us.
- **Latency:** the docs say fixtures are updated **every 15 seconds**. They add that this is indicative and may lag for some Competitions. PST and CANC fixtures are re-checked daily.
- **Statuses:** richer than football-data.org's:
  - PST (postponed; returns to Not Started once rescheduled)
  - CANC (cancelled)
  - ABD (abandoned)
  - AWD (technical loss)
  - WO (walkover)
- **Coverage:** advertised as over 1,000 leagues and cups on every plan, including free (not verified against the blocked pricing page). Only seasons and quota differ between plans.
- **Terms:**
  - Reselling the data is not allowed.
  - Apps, websites and fantasy games are the intended use.
  - The provider grants no publishing licence: rights for betting, fantasy or mass-media use are the user's responsibility.
  - The free plan can change without notice.

### Sportmonks

Sources: [plans page](https://www.sportmonks.com/football-api/plans-pricing/) and [rate-limit docs](https://docs.sportmonks.com/v3/api/rate-limit).

**Plans:**

| Plan | €/month (monthly / yearly) | Leagues | Calls/hour per entity |
|---|---|---|---|
| Free | 0 | 2 | 3,000 |
| Starter | 29 / 24 | 5 of your choice | 2,000 |
| Growth | 99 / 79 | 30 | 2,500 |
| Pro | 249 / 199 | 120 | 3,000 |
| Enterprise | custom | 2,300+ | 5,000 |

- The free plan's 2 leagues are the Danish Superliga and the Scottish Premiership.
- Paid plans come with a 14-day trial.
- Livescores are marketed as "real-time" with no latency figure.
- Starter covers only 5 leagues, so it cannot match football-data.org's free 12. Covering the top 5 plus the Champions League means Growth at €79–99/month.

## Comparison

| | football-data.org | API-Football | Sportmonks |
|---|---|---|---|
| Free tier useful for us? | **Yes**: 12 top Competitions, current season | No: past seasons only | No: Denmark and Scotland only |
| Cheapest plan covering top 5 + Champions League with live scores | €12/month (Free w/ Livescores) | $19/month (Pro) | €79–99/month (Growth) |
| Rate limit (cheapest paid) | 20/min | 7,500/day | 2,500/hour per entity |
| Documented update latency | None ("Delayed" free, "Live" paid) | 15 s, indicative | "Real-time", no figure |
| POSTPONED / AWARDED handling | POSTPONED, CANCELLED, AWARDED, SUSPENDED | PST, CANC, ABD, AWD, WO | Rich state model (not reviewed in depth) |
| Coverage ceiling | 100 Competitions at €199/month | 1,000+ on every plan | 2,300+ (Enterprise) |
| Commercial use | Allowed by omission; attribution required; crests need owner consent | Allowed for apps; no resale; licensing is user's responsibility | Paid commercial plans |
| Switching cost | None | Rewrite `football_api.py` and remap statuses and IDs | Same as API-Football |

## Recommendations

1. Stay on football-data.org. Add the attribution line to the Mini App footer.
2. Make sure scoring handles statuses other than FINISHED:
   - POSTPONED: keep the prediction open, or void it.
   - CANCELLED: void.
   - AWARDED: decide on a policy, e.g. void, or score the awarded result.
3. Before paid Leagues go live, upgrade to the €12 Livescores tier so results arrive promptly. Keep API-Football Pro ($19) as the fallback if we need more Competitions.
4. Review crest usage: proxy or self-host the images with care, or accept the risk knowingly.
5. Verify `score.fullTime` behaviour for knockout matches before cup Competitions launch.
