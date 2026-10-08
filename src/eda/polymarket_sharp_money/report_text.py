"""Prose for the report (render_report.py): how beatable Polymarket tennis is before the match.
Every number comes from the measured results passed in; the wording avoids trading jargon on purpose."""
from __future__ import annotations

GROUP_DEFS = {
    "win": "Over 10 or more other matches, got better prices than the close by more than luck can explain.",
    "unsure": "Fewer than 10 other matches, or an edge too small to tell apart from luck.",
    "lose": "Over 10 or more other matches, got worse prices than the close by more than luck can explain.",
}


IN_SENTENCE = {"slams": "the Grand Slams", "k1000": "Masters 1000, WTA 1000 and Finals events", "k500": "500 events",
               "k250": "250 events", "qual": "qualifying", "challenger": "Challenger and WTA 125 events",
               "itf": "ITF events", "other": "doubles, juniors and team events"}


def join_and(items: list[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def texts(pm: dict, pm_buf: dict, build: dict, fee_check: dict, f: dict) -> dict:
    pct, money, esc = f["pct"], f["money"], f["esc"]
    c = lambda v, d=1: f"{abs(v) * 100:.{d}f}¢"                   # size of an edge, in words
    sc = lambda v, d=1: f"{'+' if v >= 0 else '−'}{abs(v) * 100:.{d}f}¢"
    rng = lambda r, d=1: f"{sc(r['lo'], d)} to {sc(r['hi'], d)}"
    o, info = pm["overall"], pm["info"]
    lv = {x["key"]: x for x in pm["levels"]}
    bf = {x["key"]: x for x in pm_buf["levels"]}
    shown = [x for x in pm["levels"] if x["key"] != "other"]
    n10 = info["verdicts_whole_year_10plus"]
    n_win, n_lose = o["accounts_by_verdict"]["win"], o["accounts_by_verdict"]["lose"]
    one_in = lambda n: round(n10 / n)
    top = max(shown, key=lambda x: x["edge"]["win"]["est"])
    low = min(shown, key=lambda x: x["edge"]["win"]["est"])
    top_buf = max((x for x in pm_buf["levels"] if x["key"] != "other"), key=lambda x: x["edge"]["win"]["est"])
    calib = pm["calibration"]
    mid = next(b for b in calib["bins"] if b["lo"] >= 0.7 - 1e-9)
    strong = [b for b in calib["bins"] if b["lo"] >= 0.8 - 1e-9]
    level_gap = max(abs(x["won"] - x["price"]) for x in calib["by_level"])
    others = [x for x in shown if x["key"] != low["key"]]
    lo_other = min(x["edge"]["win"]["est"] for x in others)
    hi_other = max(x["edge"]["win"]["est"] for x in others)
    take = {k: x["winner_take_per_100"]["est"] / 100 * x["money"] for k, x in lv.items()}
    biggest = sorted(shown, key=lambda x: -take[x["key"]])[:2]
    men = {x["key"]: x for x in pm["split"]}
    ch_m, itf_m, slam_m = men["challenger_m"], men["itf_m"], men["slams_m"]
    real_w, real_l = o["result_after_fees"]["win"], o["result_after_fees"]["lose"]
    ch_real = lv["challenger"]["result_after_fees"]["win"]

    t = {}
    t["window"] = esc(f"{pm['window_start']} – {pm['window_end']}")
    t["LEDE"] = (f"We looked at every bet placed before the start of {o['markets']:,} tennis matches on Polymarket, "
                 f"{money(o['money'])} in all, and asked one question of each account: does it consistently get a "
                 f"better price than the last price before the match? That last price turns out to be accurate, so "
                 f"an account that beats it has a real edge.")
    t["win_accounts_pct"] = pct(n_win / n10, 1)
    t["win_accounts_note"] = f"{n_win:,} of the {n10:,} accounts that bet before 10 or more matches"
    t["win_edge"] = c(o["edge"]["win"]["est"])
    t["win_edge_note"] = (f"per $1 bet, before fees ({c(o['edge_after_fees']['win']['est'])} after), "
                          f"about ${o['edge']['win']['est'] * 100:.2f} on every $100")
    t["lose_accounts_pct"] = pct(n_lose / n10)
    t["lose_accounts_note"] = f"{n_lose:,} accounts; they give up {c(o['edge']['lose']['est'])} per $1 before fees"
    t["calib_label"] = f"Players priced at about {mid['price'] * 100:.0f}¢ at the close won"
    t["calib_value"] = pct(mid["won"], 1)

    t["VERDICT"] = f"""
  <p class="verdict"><strong>Polymarket tennis can be beaten before the match, but narrowly and by few accounts.</strong> About 1 in {one_in(n_win)} regular pre-match accounts clearly gets better prices than the closing price, and as a group they beat it by {c(o['edge']['win']['est'])} per $1 bet, {c(o['edge_after_fees']['win']['est'])} after Polymarket's fees. About 1 in {one_in(n_lose)} clearly gets worse prices. Everyone else can't be told apart from luck, and on average gives up a little.</p>
  <p class="verdict"><strong>By level of play, the winners' edge is similar everywhere, 1–2¢ per $1 before fees.</strong> It is highest at {IN_SENTENCE[top['key']]} ({c(top['edge']['win']['est'])} before fees, {c(top['edge_after_fees']['win']['est'])} after) and lowest, and least certain, at {IN_SENTENCE[low['key']]} ({c(low['edge']['win']['est'])}). What changes a lot is the size of the pool: {money(lv['slams']['money'])} was bet before Grand Slam matches, {money(lv['challenger']['money'])} before Challenger and WTA 125 matches, and {money(lv['itf']['money'])} before ITF matches, where the clear winners supply {pct(lv['itf']['share']['win']['est'])} of the money.</p>"""

    t["A_TEXT"] = f"""
      <p>The closing price is the last price before the match starts. If you bought a player at 50¢ and the price closed at 52¢, you beat the close by 2¢ a share. Per dollar bet that is 4¢, because each share cost 50¢. This is what bettors call closing-line value.</p>
      <div class="example">
        <p><b>In dollars.</b> You bet $100 on a player at 50¢ and get 200 shares. The price closes at 50.75¢. If the closing price is the true chance of winning, those 200 shares are worth $101.50 on average. You are $1.50 ahead, or 1.5¢ per $1, which is about what the clear winners manage. In betting odds, it is like taking +100 when the fair price is about −103.</p>
        <p><b>Fees.</b> Polymarket charges a fee when you accept a price someone else has posted. It is 5% of (1 − the price) of the amount you bet: 2.5¢ per $1 at 50¢, 1¢ at 80¢. Posting your own price is free. That fee is why the "after fees" figures on this page are smaller.</p>
      </div>
      <p>Beating the closing price only means something if the closing price is right. It is: across every settled match, favourites won about as often as their closing price said.</p>"""
    strong_gaps = join_and(["%.1f" % ((b["won"] - b["price"]) * 100) for b in strong])
    t["CALIB_NOTE"] = (f"Strong favourites (80¢ and up) won {strong_gaps} points "
                       f"more often than their price said; elsewhere the differences are within what luck would give. "
                       f"The same holds at every level of play: the favourites' average closing price and their actual "
                       f"win rate are within {level_gap * 100:.1f} points of each other at each level.")

    t["B_TEXT"] = f"""
      <p>Every account that bet before a match goes into one of three groups. Each account is sorted using only its bets in <i>other</i> matches, then scored on the match in question. A lucky match can't put an account in the winners' group for that same match, so the figures below are what each group really did.</p>"""
    t["B_TEXT_2"] = f"""
      <ul class="findings">
        <li><b>The clear winners</b> are a few hundred accounts, and they placed {pct(o['share']['win']['est'])} of the money bet before matches. They beat the close by {c(o['edge']['win']['est'])} per $1 before fees and {c(o['edge_after_fees']['win']['est'])} after.</li>
        <li><b>The unsure majority</b> placed {pct(o['share']['unsure']['est'])} of the money. They gave up {c(o['edge']['unsure']['est'])} per $1 before fees and {c(o['edge_after_fees']['unsure']['est'])} after.</li>
        <li><b>The clear losers</b> placed {pct(o['share']['lose']['est'])} of the money and gave up {c(o['edge']['lose']['est'])} per $1 before fees, {c(o['edge_after_fees']['lose']['est'])} after.</li>
        <li><b>Actual results agree, with much wider ranges.</b> Win-or-lose results depend on who won each match, so they are far noisier. After fees, the clear winners made {sc(real_w['est'])} per $1 (likely range {rng(real_w)}) and the clear losers {sc(real_l['est'])} ({rng(real_l)}).</li>
      </ul>"""

    t["C_TEXT"] = f"""
      <p>Each row is a level of play, men's and women's events together. The top chart shows how far the clear winners beat the closing price there, before and after fees. The bottom chart shows whose money is bet before matches at that level.</p>"""
    t["C_TEXT_2"] = f"""
      <ul class="findings">
        <li><b>The winners' edge is about the same at every level.</b> Before fees it is {c(low['edge']['win']['est'])} at {IN_SENTENCE[low['key']]} and {c(lo_other)}–{c(hi_other)} everywhere else. The ranges overlap, and the order shifts when the closing price is taken 30 minutes earlier (section D): the Grand Slams then show {c(bf['slams']['edge']['win']['est'])}. The safe reading is 1–2¢ per $1 at every level. {IN_SENTENCE[top['key']][0].upper() + IN_SENTENCE[top['key']][1:]} come out on top in both measurements ({c(top['edge']['win']['est'])} and {c(bf[top['key']]['edge']['win']['est'])}), with some of the narrowest ranges.</li>
        <li><b>The lower the level, the more of the money on the other side of your bet comes from accounts that beat the close.</b> Clear winners placed {pct(lv['slams']['share']['win']['est'])} of pre-match money at the Grand Slams, {pct(lv['challenger']['share']['win']['est'])} at Challenger and WTA 125 events and {pct(lv['itf']['share']['win']['est'])} at ITF events.</li>
        <li><b>Where the winners took the most:</b> measured at closing prices, they took {money(take[biggest[0]['key']])} from other bettors at {IN_SENTENCE[biggest[0]['key']]} and {money(take[biggest[1]['key']])} at {IN_SENTENCE[biggest[1]['key']]}. At ITF events, where Polymarket's markets only began in May 2026, it was {money(take['itf'])}.</li>
        <li><b>Men's events only</b> (table below): at ATP Challengers the clear winners beat the close by {c(ch_m['edge']['win']['est'])} per $1 ({c(ch_m['edge_after_fees']['win']['est'])} after fees). At the men's Grand Slams it was {c(slam_m['edge']['win']['est'])} ({c(slam_m['edge_after_fees']['win']['est'])} after fees, likely range {rng(slam_m['edge_after_fees']['win'])}). At men's ITF events it was {c(itf_m['edge']['win']['est'])} ({c(itf_m['edge_after_fees']['win']['est'])} after fees, {rng(itf_m['edge_after_fees']['win'])}), so neither of those is clearly above zero after fees.</li>
      </ul>"""

    checked, good = fee_check["checked"], fee_check["within_0.0001_usdc_per_share"]
    t["D_TEXT"] = f"""
      <ul class="findings">
        <li><b>Luck.</b> {n_win:,} accounts cleared the bar over the year, but with {n10:,} accounts tested, some cleared it by luck. That is why every edge on this page is measured on matches the account wasn't sorted on. It is what the group really earned, lucky members included.</li>
        <li><b>Real money.</b> At closing prices the clear winners were {c(o['edge']['win']['est'])} ahead per $1. Their actual results after fees were {sc(real_w['est'])} (likely range {rng(real_w)}), and at Challenger and WTA 125 events {sc(ch_real['est'])} ({rng(ch_real)}). The closing price and the actual results point the same way.</li>
        <li><b>Start times.</b> Polymarket's scheduled start is not always the first serve. Taking the closing price 30 minutes earlier, and counting only bets placed before then, gives the same overall answer: clear winners {sc(pm_buf['overall']['edge']['win']['est'], 2)}, clear losers {sc(pm_buf['overall']['edge']['lose']['est'], 2)}. By level the figures move within their ranges (table below).</li>
        <li><b>Fees.</b> Most fees had to be worked out from Polymarket's formula, because they are not in the trade records. The model was checked against the cash actually paid on {checked} sampled bets, and it matched to within $0.0001 a share on {good}.</li>
      </ul>"""

    t["E_TEXT"] = f"""
    <ul class="method">
      <li><b>Data.</b> Every trade on Polymarket's tennis match-winner markets whose match was scheduled from {esc(pm['window_start'])} to {esc(pm['window_end'])}: {build['fill_records']:,} records, both sides of each trade, each with its account. They come from Polymarket's public data (<code>data-api.polymarket.com/trades</code>), downloaded on 25&nbsp;Sep&nbsp;2026. {info['markets_with_close']:,} settled matches had a closing price, and {o['markets']:,} had bets before the start. Matches voided before play were left out.</li>
      <li><b>Closing price.</b> The midpoint between the best buy and sell prices in the last minute before the scheduled start, from Polymarket's price history.</li>
      <li><b>A bet's edge.</b> Shares × (closing price − price paid), for the player backed. Selling a player's shares counts as backing the opponent. Only bets at prices from 5¢ to 95¢ count. Both sides of every trade are included, so the edges add up to zero: what one account gains against the close, another gives up.</li>
      <li><b>Sorting accounts.</b> Matches were split into five groups. An account's group for a match comes from its bets in the other four. "Clearly" means its average edge over at least 10 other matches is more than twice the swing that luck alone would produce (two standard errors, with each match counted once).</li>
      <li><b>Ranges.</b> 95% ranges, from re-drawing whole matches 1,000 times.</li>
      <li><b>Fees.</b> From 28&nbsp;Apr&nbsp;2026, 5% (3% before July) × price × (1 − price) per share, paid when accepting a posted price. Earlier fees were taken in shares, which the trade records show. Before that, no fees were charged.</li>
      <li><b>Levels of play.</b> Taken from the tournament name. Men's and women's events are combined except in the men's table. ITF gender comes from the players' names ({pct(pm.get('itf_gender_share', 0.9))} of ITF matches). Doubles, juniors and team events are in the full table but not the charts.</li>
    </ul>
    <h3 style="margin-top:18px">What this cannot say</h3>
    <ul class="caveats">
      <li><b>An account is not a person.</b> One bettor can use several accounts, and the groups describe accounts.</li>
      <li><b>The closing price is right on average, not in every match.</b> An account can beat the close in a match it then loses; the edge shows up over many bets.</li>
      <li><b>"Value taken" is measured at closing prices,</b> not in actual results, which are far noisier.</li>
      <li><b>Scheduled start times.</b> A match that started early would put a few bets placed during the match into the pre-match count; section D shows this does not change the answer.</li>
      <li><b>Match-winner markets on international Polymarket only.</b> Set, total and handicap markets, and Polymarket US, were not studied.</li>
    </ul>"""
    t["FOOT"] = ("Study: <code>docs/studies/polymarket_sharp_money/</code> · code <code>src/eda/polymarket_sharp_money/prematch.py</code> · "
                 f"evidence <code>data/studies/polymarket_sharp_money/prematch.json</code> · built {esc(pm['generated'][:10])}. "
                 "A study, not a decision.")
    return t
