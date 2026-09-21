# Business-model, lifecycle and instrument profiles — concrete design

Status: proposed design and review boundary, 2026-09-19. This advances the original
SPEC 4.3 driver-model architecture and F1 applicability work. No production profile
registry, specialized metric, valuation method, schema or provider has been activated.
See [R1 scope](../../features/R1-business-aware-research.md) and the
[dated issuer evidence matrix](../../research/pilot-business-profiles-2026-09-19.md).

## The first user-facing pilot

Keep every requested ticker, in the supplied order: **CRCL, MSTR, COIN, HOOD, USAR,
MP, GOOGL**. The user said “top 5” but supplied seven; do not select or drop two.
This is a selected-company watchlist, not an interchangeable peer set or sector
universe. Preserve the independently reviewed MSFT/RBLX archives as regression
fixtures. New mappings for the seven require their own original evidence checks.
“Supported pilot set” is an implementation target, not a claim that all seven
already have a functioning live pipeline or specialized valuation.

Mining means **mineral mining** for this pilot. MSTR is a Bitcoin treasury plus
operating-business exposure, not a Bitcoin miner. Energy remains a roadmap
interest without a supplied ticker. Bitcoin-miner support is outside this first
pilot; preserve its distinct architecture for later only.

## Visible profile identity

Place a concise “Analysis profile” control in the company context, with a details
panel reachable from every profile-dependent conclusion. Display:

- Resolved issuer and exact instrument/share class; sector and theme as context.
- Primary business model and any explicit segment overlays.
- Lifecycle by business/segment: established operations, commercialization/ramp,
  development/pre-commercial or a documented mixture. Do not infer it from ticker,
  sector, market cap, a single quarter's revenue or the word “tech.”
- Assignment version, evidence date, effective date and when the evidence became
  known, with a link to the filing/announcement used.
- Metric/valuation support and outstanding prerequisites. Separate proposed,
  reviewed, unsupported and outdated assignments.
- “Suggest correction” and “Compare profile versions.” The user supplies a reason
  and evidence; a corrected assignment is a new version for subsequent analyses.

A profile is a documented analytical policy, not a score or corporate fact copied
from a sector provider. Changing it cannot rewrite saved calculations or old
assumptions. Reopen a saved run with its original profile/rule versions. A change
in classification, business mix or acquisition creates a comparison qualification,
not apparent historical operating growth. Do not retroactively insert a newly
acquired business into a prior reported period.

## What every profile must define before activation

| Policy area | Concrete requirement |
| --- | --- |
| Identity and scope | Business model, supported lifecycle states, instrument types, segment scope, version and supporting evidence. A theme such as tokenization is not a substitute for these. |
| Metrics | Relevant metrics and retained base facts; formula/source lineage; valid numerator/denominator definitions, signs, source precision, reporting periods and data/filing basis. |
| Applicability | Deterministic distinction between meaningful, N/M, not applicable, missing, stale, invalid and unsupported; map to reviewed existing flags/status contracts rather than inventing stored values. |
| Peer criteria | Comparable revenue/economic model, lifecycle, asset and financing structure, accounting/period basis, geography and regulation where relevant; display inclusion/exclusion rationale. Sector alone is insufficient. |
| Business drivers | Exact required driver observations, sources, units, gross/net basis, average/end-point basis, segment attribution and reconciliation to statements. Missing drivers do not authorize substitutes. |
| Explanations | Evidence-backed numerical comparisons and neutral rule-based observations; separate causal narratives with evidence/alternatives/uncertainty. No unsupported business cause from a ratio alone. |
| Valuation/scenarios | Methods that are reviewed and actually implemented, methods proposed for later, required inputs and assumptions, and why a method is unavailable. Do not silently apply generic FCFF to every profile. |
| Overrides | Explicit company/segment overlay, scope, evidence, author/confirmation, effective/known dates and version; no hidden hand-tuned thresholds or back-editing old runs. |

Keep losses, cash, debt, capital expenditures, financing and dilution evidence
visible even when a multiple is N/M or an advanced method is unsupported. A missing
retention metric is not zero retention and cannot give a bad business score.
No automatic universal bargain/overvalued, quality or buy/sell verdict is added.

## Required family distinctions

This is a design catalogue, not a commitment to ship every family immediately.
The dated seven-issuer matrix determines the first mapping work.

| Family / overlay | Drivers and interpretation to review | Method / data safeguards |
| --- | --- | --- |
| Established subscription/software | Recurring revenue/ARR where actually disclosed; gross/net retention; margins, cash conversion and SBC/share changes separately. | Retention definitions/cohorts differ. ARR is not reported revenue. Driver-based scenarios need reviewed reconciliation and explicit assumptions. |
| Semiconductors / hardware | Units, realized prices, product/customer mix, inventory, capacity, foundry/capex exposure and cyclicality. | Do not reuse a subscription-retention model. Distinguish fabless, integrated/foundry and equipment economics; no pilot ticker assumed. |
| Pre-commercial / early-stage | Evidenced milestones, commercialization status, committed funding, cash/debt, capex obligations and dilution. | Keep cash/cash-use facts; no unreviewed runway estimate. Funding-needs or scenario models require defined cash availability, burn/reinvestment/financing assumptions and source periods. |
| Stablecoin / float issuer | Circulation/average reserve base, reserve yield, distribution/transaction economics and retained revenue, regulatory obligations. | Reserve/customer assets are not unrestricted corporate cash. Circulation is not revenue; verify average versus period-end amounts and costs before using the original float model. |
| Fee platform / exchange | Transaction volume, actual fees/take rates, user/product mix, subscription/services, custody and stablecoin-related economics. | Token prices/volume are not company revenue; segregate principal, customer and corporate balances and distinct revenue streams. |
| Brokerage | Transaction-based versus net-interest versus other revenue, customer assets/cash, engagement and financing/regulatory capital context. | Customer assets are not corporate wealth. Net interest is not comparable to gross transaction volume. Product/segment overlays remain explicit. |
| Asset manager | Assets managed/serviced, actual fee basis, flows, performance fees and operating costs. | AUM is not revenue or owned assets; differentiate principal balance-sheet exposure. Remains future unless selected evidence warrants it. |
| Digital-asset treasury + operating business | Owned assets, realized/unrealized accounting effects, operating revenue/cash, senior debt/preferred claims, common share ownership and financing/dilution. | Preserve GAAP facts and label volatility; do not equate common NAV with bare BTC value divided by market cap. Asset, liability, tax, preferred and share-basis definitions require review. |
| Direct token/security instrument | Legal/economic rights, cash-flow claim if any, supply, redemption/ownership and market basis. | A token is not automatically an equity issuer; do not apply company EPS/FCFF by symbol. No direct token is in the supplied pilot. |
| Mineral extraction / processing / magnets | Production/sales, realized commodity prices, recovery/grade where evidenced, costs, inventory, processing capacity, reinvestment and customer qualification/ramp. | Separate operating mines, project development, separation/refining, metals/alloys and magnet manufacturing. Resource/reserve statements are not current production; planned capacity is not shipped sales. |
| Bitcoin mining (future only) | Network/owned hashrate, difficulty, realized BTC economics, power economics, uptime, fleet efficiency and capex. | Separate from mineral production and from treasury holdings; no BTC-miner ticker requested for the first pilot. |
| Energy production | Production, realized prices/hedges, costs, depletion and sustaining/growth reinvestment. | Commodity/cycle and asset-life assumptions need evidence; do not classify all energy as this model. |
| Energy transport / infrastructure | Contract/volume, tariff/toll economics, utilization and maintenance/growth capex. | Distinguish commodity ownership exposure, financing and cash-distribution definitions. |
| Utilities | Regulated asset/rate base and allowed returns where relevant, demand, capital program and funding. | Jurisdiction/regulation and capital structure differ from producers. |
| Renewable project development | Project pipeline stage, contracted economics, commissioning, financing and development-to-operation transition. | Announced pipeline is not operating generation/revenue; project versus parent debt/cash scope must match. |
| Advertising / cloud / mixed platform | Ads/services, subscription/products, cloud and other bets/segments; actual segment revenues/earnings, costs, capex and corporate allocation. | Segment-aware comparisons; do not force a SaaS or uniformly early-stage “tech” profile. SOTP is a future method subject to complete segment and corporate-claim evidence. |

## Sector views

Add a visible business-model/lifecycle composition breakdown to relevant sector
views, with classification source/version and unclassified/unsupported counts.
Allow reviewed comparison cohorts, but label their definition and population.
A filtered suitable cohort is not the original full-sector result; it needs its
own identity, coverage and exclusions. Keep sector taxonomy separate from business
profile assignment. Preserve four graphs, aggregate versus median semantics,
all existing X1 gates and fixed-snapshot drilldowns. Seven pilot stocks cannot
satisfy a ten-contributor comparison gate; do not lower gates to fill a graph.

## Bounded implementation sequence and acceptance

1. Now: finish the design/profile evidence worksheet and states for all seven;
   make “reviewed versus unsupported” explicit in Figma. This is the current slice.
2. After UI design review: inspect originals and resolve instruments/source coverage
   for the seven. Reuse existing source/precision/period calculations; record gaps
   per issuer and driver. Keep MSFT/RBLX regression tests intact.
3. Review the profile policy, missingness mapping, overlays and snapshot identity
   within D021/S6. New source concepts or stored/public fields require their normal
   sequential proposal, not a UI-driven workaround.
4. Implement one reviewed common calculation/explanation path first; progressively
   enable business-specific observations as their inputs and definitions pass tests.
   A requested ticker remains visible even if its advanced methods are unsupported.
5. Add specialized valuations only with their reviewed driver, claim/financing and
   scenario prerequisites. Preserve the original valuation backlog.

Acceptance includes: same sector/different business models do not receive identical
unsupported commentary; a loss-making company retains cash/debt/financing evidence;
a profile correction produces a new version; historical reopening uses the old
profile; acquisition dates do not contaminate pre-acquisition periods; “unknown”
metric coverage is never a bad score; and all seven requested names remain present.
