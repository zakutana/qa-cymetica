/* Cymetica's public catalogue, read 2026-10-17 by make_catalog.py (beside this file). */
const CAT={
"bots": [
{
"name": "MACD Hunter",
"sym": "MACD",
"icon": "crosshairs",
"kind": "Indicator species",
"tagline": "Momentum crossover specialist",
"desc": "Hunts for momentum shifts using MACD crossovers. Excels at catching trend changes early.",
"style": "momentum",
"risk": "medium",
"rule": "MACD 12/26/9 histogram and EMA 9/21 must agree; abstains when they disagree",
"ind": [
{
"n": "MACD",
"p": {
"fast": 12,
"slow": 26,
"signal": 9
}
},
{
"n": "MACD_Signal",
"p": {}
},
{
"n": "MACD_Histogram",
"p": {}
}
],
"clones": 1299,
"trades": 1791,
"wr": 0.40576999999999996
},
{
"name": "RSI Sniper",
"sym": "RSI",
"icon": "gauge-high",
"kind": "Indicator species",
"tagline": "Mean reversion at extremes",
"desc": "Snipes oversold and overbought conditions. Patient hunter waiting for perfect RSI setups.",
"style": "mean_reversion",
"risk": "low",
"rule": "RSI-14 on epoch closes — YES above 60 and rising, NO below 40 and falling, else sits out",
"ind": [
{
"n": "RSI",
"p": {
"period": 14,
"overbought": 70,
"oversold": 30
}
}
],
"clones": 24,
"trades": 3092,
"wr": 0.35552300000000003
},
{
"name": "Bollinger Bandit",
"sym": "BOLL",
"icon": "mask",
"kind": "Indicator species",
"tagline": "Volatility breakout trader",
"desc": "Exploits volatility expansions and contractions using Bollinger Bands. Thrives in high-volatility markets.",
"style": "volatility",
"risk": "high",
"rule": "Bollinger Bands 20/2σ on epoch closes — YES on a close above the upper band, NO below the lower band (%B, bandwidth expansion raises confidence)",
"ind": [
{
"n": "Bollinger_Bands",
"p": {
"period": 20,
"std_dev": 2
}
},
{
"n": "Bollinger_%B",
"p": {}
},
{
"n": "Bandwidth",
"p": {}
}
],
"clones": 6,
"trades": 11,
"wr": 0.36363599999999996
},
{
"name": "Volume Viper",
"sym": "VOL",
"icon": "chart-column",
"kind": "Indicator species",
"tagline": "Volume-confirmed moves only",
"desc": "Strikes only when volume confirms the move. Uses OBV, Volume Profile, and VWAP for precision entries. Live 5-minute clones of this species decide on: Prior-epoch direction (cross-market correlation) (CORR).",
"style": "momentum",
"risk": "medium",
"rule": "Prior-epoch direction (cross-market correlation)",
"ind": [
{
"n": "OBV",
"p": {}
},
{
"n": "Volume_Profile",
"p": {}
},
{
"n": "VWAP",
"p": {}
}
],
"clones": 5,
"trades": 0,
"wr": 0.0
},
{
"name": "Trend Titan",
"sym": "TREND",
"icon": "arrow-trend-up",
"kind": "Indicator species",
"tagline": "Ride the trend until it ends",
"desc": "Multi-timeframe trend follower using EMA ribbons and ADX. Holds winners, cuts losers fast.",
"style": "trend_following",
"risk": "medium",
"rule": "EMA 9/21/50 ribbon on epoch closes — YES when close > EMA9 > EMA21 > EMA50, NO when fully stacked bearish; ADX not applied (needs intrabar range)",
"ind": [
{
"n": "EMA_9",
"p": {
"period": 9
}
},
{
"n": "EMA_21",
"p": {
"period": 21
}
},
{
"n": "EMA_50",
"p": {
"period": 50
}
},
{
"n": "EMA_200",
"p": {
"period": 200
}
},
{
"n": "ADX",
"p": {
"period": 14
}
}
],
"clones": 8,
"trades": 1,
"wr": 0.0
},
{
"name": "Stochastic Striker",
"sym": "STOCH",
"icon": "hand-fist",
"kind": "Indicator species",
"tagline": "Overbought/oversold momentum plays",
"desc": "Lightning-fast striker using Stochastic oscillators. Capitalizes on momentum exhaustion.",
"style": "mean_reversion",
"risk": "medium",
"rule": "Stochastic %K(14)/%D(3) on epoch closes — YES when %K > 80 rising or > 70 above %D, NO when %K < 20 falling or < 30 below %D",
"ind": [
{
"n": "Stochastic_%K",
"p": {
"period": 14
}
},
{
"n": "Stochastic_%D",
"p": {
"period": 3
}
},
{
"n": "Stoch_RSI",
"p": {
"period": 14
}
}
],
"clones": 5,
"trades": 0,
"wr": 0.0
},
{
"name": "Ichimoku Empress",
"sym": "ICHI",
"icon": "crown",
"kind": "Indicator species",
"tagline": "Full cloud analysis mastery",
"desc": "Ancient Japanese trading wisdom. Uses all 5 Ichimoku components for complete market structure analysis.",
"style": "trend_following",
"risk": "low",
"rule": "Ichimoku on epoch closes — Tenkan 9 / Kijun 26 / Senkou A / Senkou B 52: YES above the cloud with Tenkan > Kijun, NO below with Tenkan < Kijun; Chikou not applied",
"ind": [
{
"n": "Ichimoku_Cloud",
"p": {}
},
{
"n": "Tenkan_Sen",
"p": {
"period": 9
}
},
{
"n": "Kijun_Sen",
"p": {
"period": 26
}
},
{
"n": "Chikou_Span",
"p": {
"period": 26
}
}
],
"clones": 2,
"trades": 0,
"wr": 0.0
},
{
"name": "Fibonacci Phoenix",
"sym": "FIB",
"icon": "fire",
"kind": "Indicator species",
"tagline": "Key level bounce trading",
"desc": "Rises from pullbacks at golden ratio levels. Master of Fibonacci retracements and extensions.",
"style": "mean_reversion",
"risk": "medium",
"rule": "Fibonacci retracement of the last 50 epoch closes — at a 23.6/38.2/50/61.8/78.6% level, a 5-epoch bounce is YES, a break is NO; extensions not applied",
"ind": [
{
"n": "Fib_Retracement",
"p": {
"levels": [
0.236,
0.382,
0.5,
0.618,
0.786
]
}
},
{
"n": "Fib_Extension",
"p": {
"levels": [
1.0,
1.272,
1.618,
2.0,
2.618
]
}
}
],
"clones": 19,
"trades": 3593,
"wr": 0.40043999999999996
},
{
"name": "ATR Alpha",
"sym": "ATR",
"icon": "arrows-up-down",
"kind": "Indicator species",
"tagline": "Volatility-adjusted positioning",
"desc": "Uses ATR for dynamic stop-losses and position sizing. Adapts to changing volatility conditions.",
"style": "volatility",
"risk": "high",
"rule": "ATR-14 (close-to-close) vs its 20-epoch mean — expanding volatility (>1.2x) takes the 5-epoch direction: YES up, NO down; Keltner/Chaikin not applied",
"ind": [
{
"n": "ATR",
"p": {
"period": 14
}
},
{
"n": "Keltner_Channels",
"p": {
"period": 20,
"atr_mult": 2
}
},
{
"n": "Chaikin_Volatility",
"p": {
"period": 10
}
}
],
"clones": 8,
"trades": 5,
"wr": 0.2
},
{
"name": "Divergence Dragon",
"sym": "DIV",
"icon": "dragon",
"kind": "Indicator species",
"tagline": "Reversal detection master",
"desc": "Breathes fire on divergence setups. Spots hidden and regular divergences between price and indicators. Live 5-minute clones of this species decide on: Fades prior-epoch rallies; rides existing downtrends (FADE).",
"style": "reversal",
"risk": "high",
"rule": "Fades prior-epoch rallies; rides existing downtrends",
"ind": [
{
"n": "RSI_Divergence",
"p": {
"period": 14
}
},
{
"n": "MACD_Divergence",
"p": {}
},
{
"n": "OBV_Divergence",
"p": {}
}
],
"clones": 3,
"trades": 0,
"wr": 0.0
},
{
"name": "Perceptron Oracle",
"sym": "PCPN",
"icon": "brain",
"kind": "Indicator species",
"tagline": "Neural signal weighting — learns from every trade",
"desc": "Uses a three-layer perceptron neural network to automatically learn optimal signal weights from trade outcomes. Layer 1 (Species): learns per-species TA signal combinations. Layer 2 (Ensemble): combines all 10 species into consensus predictions. Layer 3 (Clone): inherits species weights at clone time, then diverges via your own trade history. Replaces hardcoded 70/30 heuristic with online gradient descent — gets smarter every epoch. Live 5-minute clones of this species decide on: Single-layer perceptron on five epoch-close features (1/3/10-epoch returns, RSI-14, 5-vs-20 volatility ratio), retrained online by gradient descent over the clone's window before every decision — YES at a score ≥ 0.60, NO at ≤ 0.40, else sits out (PCPN).",
"style": "neural_ensemble",
"risk": "medium",
"rule": "Single-layer perceptron on five epoch-close features (1/3/10-epoch returns, RSI-14, 5-vs-20 volatility ratio), retrained online by gradient descent over the clone's window before every decision — YES at a score ≥ 0.60, NO at ≤ 0.40, else sits out",
"ind": [
{
"n": "Perceptron_Species",
"p": {
"inputs": 5,
"activation": "sigmoid"
}
},
{
"n": "Perceptron_Ensemble",
"p": {
"inputs": 10,
"activation": "sigmoid"
}
},
{
"n": "Perceptron_Clone",
"p": {
"inputs": 5,
"activation": "sigmoid",
"inherits": "species"
}
}
],
"clones": 10,
"trades": 3966,
"wr": 0.35706400000000005
},
{
"name": "Liquidation Hunter",
"sym": "LIQHUNT",
"icon": "bullseye",
"kind": "Perpetual agent",
"tagline": "Exploit leveraged liquidation cascades",
"desc": "Identifies over-leveraged positions using 5-pillar analysis: liquidation heatmap (pool imbalance), funding rate pressure, OI buildup patterns, Fibonacci confluence, and volume confirmation. Executes Bear Hunts (bet NO when longs are over-leveraged) and Bull Hunts (bet YES when shorts are squeezable).",
"style": "liqhunt",
"risk": "high",
"rule": null,
"ind": [],
"clones": 2,
"trades": 0,
"wr": 0.0
},
{
"name": "Stat Oracle",
"sym": "STAT",
"icon": "chart-simple",
"kind": "Perpetual agent",
"tagline": "Statistical edge finder",
"desc": "Uses statistical analysis of recent epoch outcomes to identify streaks and reversion patterns. Data-driven decision making.",
"style": "stat",
"risk": "low",
"rule": null,
"ind": [],
"clones": 2,
"trades": 366,
"wr": 0.34153
},
{
"name": "Sync Master",
"sym": "SYNC",
"icon": "arrows-rotate",
"kind": "Perpetual agent",
"tagline": "Hedged alternation specialist",
"desc": "Alternates YES/NO positions across epochs for balanced exposure. Captures variance while minimizing directional risk.",
"style": "sync",
"risk": "low",
"rule": null,
"ind": [],
"clones": 2,
"trades": 706,
"wr": 0.439093
},
{
"name": "Fade the Rally",
"sym": "FADE",
"icon": "arrow-trend-down",
"kind": "Perpetual agent",
"tagline": "Contrarian downside specialist",
"desc": "Fades rallies with NO bets. Stronger conviction when rallies are bigger. Rides existing downtrends with moderate NO positions.",
"style": "fade",
"risk": "high",
"rule": null,
"ind": [],
"clones": 2,
"trades": 699,
"wr": 0.5092990000000001
},
{
"name": "Corr Catcher",
"sym": "CORR",
"icon": "link",
"kind": "Perpetual agent",
"tagline": "Cross-market correlation trader",
"desc": "Exploits correlations between crypto assets. Reads BTC momentum to predict ETH direction, using cross-market signals.",
"style": "corr",
"risk": "medium",
"rule": null,
"ind": [],
"clones": 2,
"trades": 281,
"wr": 0.181495
},
{
"name": "Crash Detector",
"sym": "CRASH",
"icon": "burst",
"kind": "Perpetual agent",
"tagline": "Consecutive drop streak rider",
"desc": "Tracks consecutive NO-win epochs and rides crash streaks. When drops cluster, conviction grows. Hedges mildly bullish when no streak detected.",
"style": "crash",
"risk": "high",
"rule": null,
"ind": [],
"clones": 2,
"trades": 212,
"wr": 0.287736
},
{
"name": "Vortex Drain",
"sym": "VORTX",
"icon": "hurricane",
"kind": "Perpetual agent",
"tagline": "Time-cycle selling pressure",
"desc": "Uses epoch modular arithmetic to identify cyclical selling windows. Bets NO during selling pressure phases, hedges YES during recovery windows.",
"style": "vortx",
"risk": "low",
"rule": null,
"ind": [],
"clones": 2,
"trades": 676,
"wr": 0.491124
},
{
"name": "Doom & Gloom",
"sym": "GLOOM",
"icon": "moon",
"kind": "Perpetual agent",
"tagline": "Volatility pessimist",
"desc": "Measures last epoch price swings. High volatility signals fear and falling prices. Scales NO confidence with swing magnitude.",
"style": "gloom",
"risk": "medium",
"rule": null,
"ind": [],
"clones": 1,
"trades": 652,
"wr": 0.328221
},
{
"name": "Sent Surfer",
"sym": "SENT",
"icon": "water",
"kind": "Perpetual agent",
"tagline": "Sentiment momentum rider",
"desc": "Rides momentum waves with confidence scaling. Higher conviction when price trends are sustained, adapts to sentiment shifts.",
"style": "sent",
"risk": "high",
"rule": null,
"ind": [],
"clones": 2,
"trades": 244,
"wr": 0.278689
},
{
"name": "Delta Hunter",
"sym": "DELTA",
"icon": "bolt",
"kind": "Perpetual agent",
"tagline": "Mean reversion specialist",
"desc": "Hunts price reversals after large swings. Bets on reversion when volatility spikes, follows trend when markets are calm.",
"style": "delta",
"risk": "medium",
"rule": null,
"ind": [],
"clones": 2,
"trades": 356,
"wr": 0.328652
},
{
"name": "Dread Gauge",
"sym": "DREAD",
"icon": "newspaper",
"kind": "Perpetual agent",
"tagline": "News-driven bearish signal",
"desc": "Reads scored headlines for high-impact bearish news. Higher average impact scores drive stronger NO conviction. Falls back to mild bull when news is calm.",
"style": "dread",
"risk": "medium",
"rule": null,
"ind": [],
"clones": 1,
"trades": 711,
"wr": 0.398031
}
],
"algos": [
{
"name": "MACD Crossover",
"icon": "chart-simple",
"cat": "Technical indicator",
"desc": "Moving Average Convergence Divergence signal detection",
"params": [
{
"label": "Fast Period",
"min": 5.0,
"max": 50.0,
"def": 12.0
},
{
"label": "Slow Period",
"min": 10.0,
"max": 100.0,
"def": 26.0
},
{
"label": "Signal Period",
"min": 3.0,
"max": 20.0,
"def": 9.0
}
],
"free": true
},
{
"name": "RSI Momentum",
"icon": "gauge",
"cat": "Technical indicator",
"desc": "Relative Strength Index overbought/oversold signals",
"params": [
{
"label": "Period",
"min": 5.0,
"max": 50.0,
"def": 14.0
},
{
"label": "Overbought",
"min": 60.0,
"max": 90.0,
"def": 70.0
},
{
"label": "Oversold",
"min": 10.0,
"max": 40.0,
"def": 30.0
}
],
"free": true
},
{
"name": "Bollinger Bands",
"icon": "water",
"cat": "Technical indicator",
"desc": "Volatility-based mean reversion entries",
"params": [
{
"label": "Period",
"min": 10.0,
"max": 50.0,
"def": 20.0
},
{
"label": "Std Dev",
"min": 1.0,
"max": 4.0,
"def": 2.0
}
],
"free": true
},
{
"name": "Volume Spike",
"icon": "bolt",
"cat": "Technical indicator",
"desc": "Detect unusual volume for breakout confirmation",
"params": [
{
"label": "Threshold",
"min": 1.5,
"max": 5.0,
"def": 2.0
},
{
"label": "Lookback",
"min": 5.0,
"max": 50.0,
"def": 20.0
}
],
"free": true
},
{
"name": "Fibonacci Retracement",
"icon": "bullseye",
"cat": "Technical indicator",
"desc": "Key support/resistance level identification",
"params": [
{
"label": "Depth",
"min": 10.0,
"max": 100.0,
"def": 50.0
}
],
"free": true
},
{
"name": "Mean Reversion",
"icon": "arrows-rotate",
"cat": "Technical indicator",
"desc": "Statistical reversion to moving averages",
"params": [
{
"label": "Window",
"min": 10.0,
"max": 200.0,
"def": 50.0
},
{
"label": "Z-Score",
"min": 1.0,
"max": 3.0,
"def": 2.0
}
],
"free": true
},
{
"name": "EMA Crossover",
"icon": "code-merge",
"cat": "Technical indicator",
"desc": "Fast EMA above slow EMA = long, below = flat",
"params": [
{
"label": "Fast Period",
"min": 5.0,
"max": 30.0,
"def": 9.0
},
{
"label": "Slow Period",
"min": 20.0,
"max": 100.0,
"def": 21.0
}
],
"free": true
},
{
"name": "ADX Trend Filter",
"icon": "compass",
"cat": "Technical indicator",
"desc": "Only enter while the trend strength (ADX) is above the floor",
"params": [
{
"label": "Period",
"min": 7.0,
"max": 30.0,
"def": 14.0
},
{
"label": "Min ADX",
"min": 15.0,
"max": 35.0,
"def": 25.0
}
],
"free": true
},
{
"name": "Genomic Momentum",
"sym": "HELIX",
"icon": "dna",
"cat": "Momentum",
"tagline": "DNA-inspired multi-timeframe momentum cascades",
"desc": "Gene expression cascade patterns applied to multi-timeframe EMA/MACD/ADX alignment.",
"eli5": "Looks at whether prices are moving up across multiple timeframes (short, medium, long). When all timeframes agree the trend is up, it buys. Like checking the weather forecast for today, this week, and this month — if all say sunny, pack sunscreen.",
"ex": "HELIX sees BTC rising on the 1-hour, 4-hour, and daily charts simultaneously → signals BUY because all timeframes confirm the uptrend.",
"level": 3,
"defaults": {
"ema_periods": [
9,
21,
50
]
},
"free": true,
"price": null
},
{
"name": "Protein Folding Arbitrage",
"sym": "PRION",
"icon": "puzzle-piece",
"cat": "Arbitrage",
"tagline": "Structural arbitrage from misfolded price relationships",
"desc": "Cross-market correlation folding/misfolding detection for structural arbitrage.",
"eli5": "Finds pairs of assets that normally move together but have temporarily diverged. Buys the cheap one, sells the expensive one, and profits when they snap back together.",
"ex": "ETH and BTC usually move in sync. ETH drops 5% while BTC is flat → PRION buys ETH expecting it to catch up.",
"level": 4,
"defaults": {},
"free": false,
"price": 9.99
},
{
"name": "Michaelis-Menten Reversion",
"sym": "ENZYME",
"icon": "flask",
"cat": "Mean reversion",
"tagline": "Kinetic mean reversion at enzymatic saturation points",
"desc": "Enzyme kinetics applied to Bollinger Band and z-score reversion timing.",
"eli5": "Buys when price drops too far too fast, expecting a bounce back to normal. Like a rubber band — the more you stretch it, the harder it snaps back.",
"ex": "A prediction market drops from 65% to 45% in one hour on no news → ENZYME buys at 45%, expecting a bounce back toward 60%.",
"level": 4,
"defaults": {},
"free": true,
"price": null
},
{
"name": "Neural Oscillation Hedging",
"sym": "SYNAPSE",
"icon": "brain",
"cat": "Hedging",
"tagline": "Frequency-band hedging inspired by neural oscillations",
"desc": "Fourier decomposition of price into frequency bands for hedging.",
"eli5": "Splits price movement into fast waves and slow waves. Uses fast waves for quick trades and slow waves to understand the bigger picture. Hedges one against the other.",
"ex": "Price is trending up slowly but oscillating wildly in 5-minute candles → SYNAPSE buys the dips in the fast cycle while the slow trend is still up.",
"level": 5,
"defaults": {},
"free": false,
"price": 14.99
},
{
"name": "Evolutionary Game Theory",
"sym": "CORTEX",
"icon": "chess-knight",
"cat": "Game theory",
"tagline": "Predator-prey dynamics on prediction market populations",
"desc": "Lotka-Volterra predator-prey dynamics applied to YES/NO pool populations.",
"eli5": "Watches how many people are buying YES vs NO in a market. When one side gets too crowded, it bets against them — the crowd often overshoots.",
"ex": "A market has 80% YES buyers and price is at 75% → CORTEX sells YES, betting the crowd is overpaying and price will correct.",
"level": 4,
"defaults": {},
"free": true,
"price": null
},
{
"name": "Decay Curve Options Pricing",
"sym": "TELOMERE",
"icon": "hourglass-half",
"cat": "Options pricing",
"tagline": "Biological time-decay curves for binary options",
"desc": "Binary options theta decay modeled after telomere shortening.",
"eli5": "Prediction markets must end at 0% or 100%. As deadline approaches, time decay accelerates. This model prices that decay — like options expiring, the closer to the end, the faster value drains.",
"ex": "A market at 60% has 2 days left. TELOMERE calculates that time decay alone should push it to 55% by tomorrow if nothing changes → sells YES.",
"level": 5,
"defaults": {},
"free": false,
"price": 14.99
},
{
"name": "Adaptive Sentiment Defense",
"sym": "IMMUNE",
"icon": "shield-virus",
"cat": "Sentiment",
"tagline": "Immunological memory for recurring sentiment patterns",
"desc": "Models the adaptive immune system memory for sentiment shocks.",
"eli5": "Remembers how the market reacted to similar news in the past. If \"Fed raises rates\" crashed prices 3 times before, it expects the same reaction next time.",
"ex": "Inflation data comes out hot. IMMUNE recalls that the last 4 hot CPI prints caused a 3% dip within 2 hours → preemptively sells.",
"level": 3,
"defaults": {},
"free": true,
"price": null
},
{
"name": "Time-Cycle Volatility",
"sym": "CIRCADIAN",
"icon": "clock",
"cat": "Volatility",
"tagline": "Session-boundary volatility from biological clock patterns",
"desc": "Maps 24-hour and weekly volatility cycles to trading session boundaries.",
"eli5": "Markets are more volatile at certain times of day (e.g., US market open) and calmer at others (e.g., weekends). This trades the predictable rhythm.",
"ex": "Volatility spikes every day at 9:30 AM ET when US markets open. CIRCADIAN places breakout orders at 9:25 AM to catch the move.",
"level": 2,
"defaults": {},
"free": true,
"price": null
},
{
"name": "Position Splitting Compounder",
"sym": "MITOSIS",
"icon": "circle-nodes",
"cat": "Position mgmt",
"tagline": "Kelly-criterion cell division for geometric compounding",
"desc": "Kelly-criterion position splitting at profit thresholds.",
"eli5": "When you are winning, it gradually increases your bet size. When losing, it shrinks bets. This compounds winners and limits damage from losers.",
"ex": "After 3 winning trades, MITOSIS increases position size from $10 to $15. After a loss, it drops back to $10 to protect profits.",
"level": 2,
"defaults": {},
"free": true,
"price": null
},
{
"name": "Precision Market Editing",
"sym": "CRISPR",
"icon": "crosshairs",
"cat": "Precision entry",
"tagline": "Multi-signal confluence for surgical trade execution",
"desc": "Multi-signal confluence before executing, inspired by CRISPR-Cas9.",
"eli5": "Only takes a trade when multiple signals agree at the same time. Like a surgeon who only operates when all tests confirm the diagnosis — fewer trades but much higher accuracy.",
"ex": "RSI says oversold, MACD shows bullish crossover, AND volume is above average → CRISPR fires a BUY. If only 2 of 3 agree, it waits.",
"level": 3,
"defaults": {},
"free": true,
"price": null
},
{
"name": "MIRAGE",
"sym": "MIRAGE",
"icon": "ghost",
"cat": "Probability",
"tagline": "Detects thin-liquidity drift and trades snap-back when volume returns",
"desc": "Detects thin-liquidity drift and trades snap-back when volume returns",
"eli5": "When price drifts on low volume (few people trading), it is unreliable. This model waits for volume to return, then bets the price will snap back to where it was.",
"ex": "Price drifted from 50% to 58% overnight on almost no volume. Morning volume returns → MIRAGE sells YES at 58%, expecting a snap-back to ~52%.",
"level": 3,
"defaults": {
"fat_volume_ratio": 1.5,
"min_displacement": 0.03,
"thin_volume_ratio": 0.3
},
"free": true,
"price": null
},
{
"name": "DRIFT",
"sym": "DRIFT",
"icon": "wind",
"cat": "Probability",
"tagline": "Hurst exponent detects trending vs mean-reverting regimes on log-odds returns",
"desc": "Hurst exponent detects trending vs mean-reverting regimes on log-odds returns",
"eli5": "Measures whether recent price moves are likely to continue (trending) or reverse (mean-reverting). Uses math to tell the difference, then picks the right strategy.",
"ex": "DRIFT detects that this market has been trending for 3 days with a Hurst exponent of 0.7 (>0.5 = trending) → follows the trend instead of fading it.",
"level": 3,
"defaults": {
"hurst_window": 40,
"momentum_window": 10,
"hurst_trend_threshold": 0.6,
"hurst_revert_threshold": 0.4
},
"free": true,
"price": null
},
{
"name": "RUPTURE",
"sym": "RUPTURE",
"icon": "burst",
"cat": "Probability",
"tagline": "Bayesian change-point detection for probability regime shifts",
"desc": "Bayesian change-point detection for probability regime shifts",
"eli5": "Detects when the market is suddenly shifting to a new reality. Like detecting that \"we are in a new era now\" moment and repositioning fast.",
"ex": "A political candidate drops out — the market was at 40% and needs to completely reprice. RUPTURE detects the regime shift and sells immediately.",
"level": 3,
"defaults": {
"lookback": 20,
"hazard_lambda": 100,
"drift_threshold": 0.02
},
"free": true,
"price": null
},
{
"name": "ANCHOR",
"sym": "ANCHOR",
"icon": "anchor",
"cat": "Probability",
"tagline": "Trades OU mean-reversion around dynamically estimated fair value in log-odds space",
"desc": "Trades OU mean-reversion around dynamically estimated fair value in log-odds space",
"eli5": "Finds the \"fair value\" of a prediction market and buys when price drops below it, sells when price rises above it. Like knowing a house is worth $300K and buying when it dips to $280K.",
"ex": "ANCHOR estimates fair value at 55%. Price spikes to 65% on a rumor → ANCHOR sells YES, expecting it to fall back toward 55%.",
"level": 3,
"defaults": {
"min_theta": 0.05,
"ou_window": 50,
"exit_zscore": 0.3,
"entry_zscore": 1.5
},
"free": true,
"price": null
},
{
"name": "ENDGAME",
"sym": "ENDGAME",
"icon": "flag-checkered",
"cat": "Probability",
"tagline": "Exploits mandatory convergence to 0/1 in final phase of market life",
"desc": "Exploits mandatory convergence to 0/1 in final phase of market life",
"eli5": "As a prediction market approaches its end date, the price MUST go to either 0 or 100. This model trades the acceleration toward the final outcome in the last hours/days.",
"ex": "An election market is at 85% with 6 hours to go and leading in all exit polls → ENDGAME buys YES at 85% for near-certain convergence to 100%.",
"level": 3,
"defaults": {
"lookback": 10,
"prob_threshold": 0.15,
"time_threshold": 0.3,
"acceleration_min": 0.001
},
"free": true,
"price": null
},
{
"name": "RECOIL",
"sym": "RECOIL",
"icon": "rotate-left",
"cat": "Probability",
"tagline": "Classifies large moves by post-shock volatility decay rate",
"desc": "Classifies large moves by post-shock volatility decay rate",
"eli5": "After a big sudden price move, this model figures out if it was real news (price keeps going) or just a panic/hype spike (price bounces back). Trades accordingly.",
"ex": "Price drops 10% in 5 minutes. RECOIL checks if volume supports the move — low volume means it was a thin-liquidity panic → buys the dip.",
"level": 3,
"defaults": {
"decay_window": 8,
"move_threshold": 0.08,
"fast_decay_ratio": 0.5,
"slow_decay_ratio": 0.8
},
"free": true,
"price": null
},
{
"name": "VERDICT",
"sym": "VERDICT",
"icon": "gavel",
"cat": "Probability",
"tagline": "Trades Shannon entropy collapse S-curve preceding resolution",
"desc": "Trades Shannon entropy collapse S-curve preceding resolution",
"eli5": "When a market is about to be resolved (decided), the uncertainty drops fast. This model detects that \"certainty rush\" and rides it before others catch on.",
"ex": "Election results are trickling in and uncertainty is collapsing fast. VERDICT detects the S-curve acceleration and buys the leading outcome early.",
"level": 3,
"defaults": {
"entropy_window": 15,
"accel_threshold": -0.002,
"min_entropy_drop": 0.1,
"min_prob_distance": 0.1
},
"free": true,
"price": null
},
{
"name": "FLUX",
"sym": "FLUX",
"icon": "wave-square",
"cat": "Probability",
"tagline": "High-vol = momentum, low-vol = mean-reversion via vol ratio regime detection",
"desc": "High-vol = momentum, low-vol = mean-reversion via vol ratio regime detection",
"eli5": "Detects whether the market is in a \"choppy\" or \"trendy\" phase. In trendy phases it follows momentum; in choppy phases it trades mean reversion. Switches automatically.",
"ex": "Market has been ranging 48-52% for a week (low volatility) → FLUX uses mean reversion, buying at 48% and selling at 52%.",
"level": 3,
"defaults": {
"vol_long": 30,
"vol_short": 5,
"regime_threshold": 1.3,
"reversion_zscore": 1.2
},
"free": true,
"price": null
},
{
"name": "SIGNAL",
"sym": "SIGNAL",
"icon": "tower-broadcast",
"cat": "Probability",
"tagline": "Volume-confirmed shocks continue; low-volume shocks revert",
"desc": "Volume-confirmed shocks continue; low-volume shocks revert",
"eli5": "When a big news event hits AND volume spikes too, the move is real — ride it. When price moves on low volume, it is probably fake — fade it.",
"ex": "Breaking news causes a 5% price jump with 10x normal volume → SIGNAL buys and holds. Same jump on normal volume → SIGNAL fades the move.",
"level": 3,
"defaults": {
"hold_candles": 5,
"shock_zscore": 2.5,
"volume_confirm_ratio": 2.0
},
"free": true,
"price": null
},
{
"name": "ORACLE",
"sym": "ORACLE",
"icon": "eye",
"cat": "Probability",
"tagline": "Trades against miscalibrated probability bins using cross-market outcome data",
"desc": "Trades against miscalibrated probability bins using cross-market outcome data",
"eli5": "Looks at whether prediction market bookmakers have historically been wrong at certain probability levels. If markets at 70% actually resolve YES only 60% of the time, it bets NO.",
"ex": "Markets priced at 80% have historically only been correct 72% of the time → ORACLE sells YES at 80%, profiting from the consistent overpricing.",
"level": 3,
"defaults": {
"n_bins": 10,
"min_samples": 5,
"edge_threshold": 0.05,
"resolved_outcomes": []
},
"free": true,
"price": null
}
],
"skills": [
{
"name": "Stop Loss",
"icon": "shield-halved",
"cat": "Risk",
"desc": "Automated risk management with trailing stops",
"free": true,
"slot": "risk"
},
{
"name": "Take Profit",
"icon": "sack-dollar",
"cat": "Risk",
"desc": "Lock in gains at target price levels",
"free": true,
"slot": "risk"
},
{
"name": "Position Sizing",
"icon": "shield-halved",
"cat": "Risk",
"desc": "Kelly criterion-based allocation",
"free": true,
"slot": "risk"
},
{
"name": "Time Filter",
"icon": "shield-halved",
"cat": "Risk",
"desc": "Trade only during optimal market hours",
"free": true,
"slot": "risk"
},
{
"name": "Diversification",
"icon": "chart-pie",
"cat": "Risk",
"desc": "Multi-asset portfolio balancing",
"free": true,
"slot": "risk"
},
{
"name": "AI Optimize",
"icon": "robot",
"cat": "Risk",
"desc": "Machine learning parameter tuning",
"free": true,
"slot": "risk"
},
{
"name": "Performance Boost (70/30)",
"icon": "rocket",
"cat": "Strategy modifier",
"desc": "Blends 70% historical win-rate data with 30% live TA signals. Favors historically profitable setups.",
"eli5": "Blends past performance data (what worked historically) with live signals (what is happening now). 70% history, 30% real-time. Best of both worlds.",
"ex": "Historical data says this setup wins 80% of the time. Live RSI confirms oversold. Performance Boost gives it a high confidence score → BUY.",
"slot": "passive",
"free": true,
"live": true,
"used": [
"MACD Hunter",
"RSI Sniper",
"Fibonacci Phantom",
"Bull McBullface"
]
},
{
"name": "MACD Crossover",
"icon": "chart-line",
"cat": "Ta indicator",
"desc": "Detects bullish/bearish MACD line crossovers for momentum shifts. Core signal for trend-following bots.",
"eli5": "Detects when momentum shifts from bullish to bearish (or vice versa) by watching two moving average lines cross. One of the most popular trading signals.",
"ex": "MACD line crosses above the signal line → bullish crossover, bot buys. MACD crosses below → bearish, bot sells.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"MACD Hunter",
"EMA Sentinel",
"Delta Hunter",
"Sync Master"
]
},
{
"name": "RSI Momentum",
"icon": "gauge-high",
"cat": "Ta indicator",
"desc": "Uses Relative Strength Index to detect overbought/oversold zones. Triggers entries at RSI extremes.",
"eli5": "Measures if something is \"overbought\" (too expensive, likely to drop) or \"oversold\" (too cheap, likely to bounce). Scale of 0-100; below 30 = oversold, above 70 = overbought.",
"ex": "RSI drops to 25 (deeply oversold) → bot buys, expecting a bounce. RSI hits 80 (overbought) → bot sells or takes profit.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"RSI Sniper",
"Stochastic Striker",
"Delta Hunter",
"Sync Master",
"Fade the Rally"
]
},
{
"name": "Binance WebSocket",
"icon": "bolt",
"cat": "Data feed",
"desc": "Real-time price feed from Binance. Sub-second price updates for faster signal generation.",
"eli5": "Gives your bot super-fast price updates from Binance (the world's biggest crypto exchange). Faster data = faster reactions to price changes.",
"ex": "Price drops 2% on Binance in under a second. Your bot sees it instantly and sells before the EventTrader price catches up.",
"slot": "secondary",
"free": true,
"live": true,
"used": [
"Corr Catcher"
]
},
{
"name": "Volume Threshold",
"icon": "gauge",
"cat": "Filter",
"desc": "Only allows trades when volume exceeds rolling average. Ensures sufficient market participation.",
"eli5": "Only allows trades when enough people are trading (high volume). Low volume = unreliable price moves. It is like only playing poker when the table is full.",
"ex": "Your bot gets a BUY signal, but volume is 80% below average → Volume Threshold blocks the trade to avoid a thin-market trap.",
"slot": "secondary",
"free": true,
"live": true,
"used": [
"EMA Sentinel",
"Vortex Drain"
]
},
{
"name": "Bollinger Squeeze",
"icon": "compress",
"cat": "Ta indicator",
"desc": "Identifies volatility contraction (squeeze) before explosive moves. Catches breakouts early.",
"eli5": "Detects when a price is coiling tightly (low volatility squeeze). Like a spring being compressed — when it releases, a big move follows. Your bot catches the breakout.",
"ex": "Bollinger Bands are the tightest they have been in 30 days → Bollinger Squeeze alerts your bot to prepare for a breakout in either direction.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Bollinger Bandit",
"Volatility Viper",
"Doom & Gloom"
]
},
{
"name": "Volatility Filter",
"icon": "filter",
"cat": "Filter",
"desc": "Blocks trades during extreme volatility spikes. Protects against whipsaws and flash crashes.",
"eli5": "Blocks your bot from trading during wild, unpredictable price swings. Prevents getting chopped up by whipsaws. Like staying indoors during a storm.",
"ex": "A major hack causes 20% swings in 10 minutes. Volatility Filter blocks all trades until the storm passes.",
"slot": "secondary",
"free": true,
"live": true,
"used": [
"Volatility Viper",
"Fade the Rally",
"Bear Grylls",
"Crash Detector"
]
},
{
"name": "EMA Trend",
"icon": "arrow-trend-up",
"cat": "Ta indicator",
"desc": "Uses 8/21/50 EMA alignment to confirm trend direction. Filters out counter-trend noise.",
"eli5": "Uses 3 moving averages (fast, medium, slow) to confirm trend direction. When all 3 line up pointing the same way, the trend is strong.",
"ex": "9-day EMA > 21-day EMA > 50-day EMA and all pointing up → strong uptrend confirmed, bot only takes BUY signals.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"MACD Hunter",
"EMA Sentinel",
"Ichimoku Oracle",
"Sync Master",
"Bull McBullface"
]
},
{
"name": "Ichimoku Cloud",
"icon": "cloud",
"cat": "Ta indicator",
"desc": "Multi-dimensional support/resistance using Tenkan, Kijun, and Kumo cloud. Full trend picture.",
"eli5": "An all-in-one trend indicator from Japan. Shows trend direction, momentum, and support/resistance all at once. When price is above the \"cloud,\" the trend is up.",
"ex": "Price breaks above the Ichimoku cloud with a bullish Tenkan/Kijun cross → strong BUY signal with multiple confirmations.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Ichimoku Oracle"
]
},
{
"name": "ATR Volatility",
"icon": "wave-square",
"cat": "Ta indicator",
"desc": "Uses Average True Range to size positions and set dynamic stop-losses based on volatility.",
"eli5": "Measures how wildly a price is swinging and sizes your trades accordingly. Big swings = smaller bets. Small swings = bigger bets. Also sets stop-losses automatically.",
"ex": "BTC volatility is 2x normal → ATR cuts position size in half and widens stop-loss to avoid getting stopped out by noise.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Bollinger Bandit",
"Volatility Viper",
"Bear Grylls",
"Crash Detector",
"Doom & Gloom"
]
},
{
"name": "Global Liquidity Regime",
"icon": "globe",
"cat": "Filter",
"desc": "Monitors macro liquidity conditions (M2 supply, Fed balance sheet). Only trades in favorable regimes.",
"eli5": "Monitors big-picture money supply (how much cash is sloshing around the global economy). Only lets your bot trade when conditions are favorable. Think of it as a \"macro weather check.\"",
"ex": "The Fed is printing money (M2 supply rising) → bullish regime, bot trades aggressively. Fed is tightening → bot goes cautious.",
"slot": "secondary",
"free": true,
"live": true,
"used": [
"Ichimoku Oracle",
"Corr Catcher",
"Dread Gauge"
]
},
{
"name": "Volume Profile",
"icon": "chart-bar",
"cat": "Ta indicator",
"desc": "Tracks volume at price levels to find high-activity zones. Identifies strong support/resistance.",
"eli5": "Maps where most trading activity has happened at each price level. Heavy-volume price levels act as strong support or resistance — price tends to bounce off them.",
"ex": "Most volume traded between $48-$52. Price drops to $48 → Volume Profile shows strong support, bot buys expecting a bounce.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Fibonacci Phantom",
"Stat Oracle",
"Vortex Drain"
]
},
{
"name": "Momentum Rider",
"icon": "forward-fast",
"cat": "Strategy modifier",
"desc": "Doubles down on winning streaks. Increases position size after consecutive wins.",
"eli5": "When your bot is on a winning streak, it increases bet size to compound gains. Ride the hot hand — but it also knows when to pull back.",
"ex": "Bot wins 5 trades in a row → Momentum Rider doubles position size on the 6th trade to maximize the streak. After a loss, it resets.",
"slot": "passive",
"free": true,
"live": true,
"used": [
"Stochastic Striker",
"Sent Surfer",
"Bull McBullface"
]
},
{
"name": "Headline Sentiment",
"icon": "newspaper",
"cat": "Sentiment",
"desc": "AI-powered news headline analysis. Scores sentiment from major crypto news sources in real-time.",
"eli5": "Reads the latest news headlines and scores them as positive, negative, or neutral. Your bot reacts to news before most humans even read it.",
"ex": "Breaking: \"Major partnership announced for Project X\" → Headline Sentiment scores it +0.85 (very positive) → bot buys.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Sent Surfer",
"Dread Gauge"
]
},
{
"name": "Contrarian Mode",
"icon": "shuffle",
"cat": "Strategy modifier",
"desc": "Inverts primary signal direction. Bets against the crowd when confidence is high.",
"eli5": "Flips your bot's signals: when it would normally buy, it sells instead. Useful when the crowd is usually wrong — bet against them.",
"ex": "Everyone is piling into YES at 80%. Contrarian Mode flips to NO, betting the crowd is overpaying. If price drops back to 70%, it profits.",
"slot": "passive",
"free": true,
"live": true,
"used": [
"Delta Hunter",
"Fade the Rally",
"Bear Grylls",
"Crash Detector",
"Dread Gauge",
"Doom & Gloom"
]
},
{
"name": "Market Making",
"icon": "scale-balanced",
"cat": "Strategy modifier",
"desc": "Provides two-sided liquidity by posting bid and ask orders around mid price. Captures spread while managing inventory risk via position limits and drift re-quoting.",
"eli5": "Your bot places both buy and sell orders around the current price, earning the spread (the gap between buy and sell prices). It profits from every trade, not from price direction.",
"ex": "Current price is 50%. Bot places a buy at 49% and a sell at 51%. When both fill, it earns 2% spread regardless of which way the market goes.",
"slot": "passive",
"free": true,
"live": true,
"used": [
"Stat Oracle",
"Vortex Drain"
]
},
{
"name": "Fibonacci Levels",
"icon": "hurricane",
"cat": "Ta indicator",
"desc": "Auto-calculates Fibonacci retracement levels from swing highs/lows. Targets key pullback zones.",
"eli5": "Auto-draws support and resistance lines based on key mathematical ratios (38.2%, 50%, 61.8%). These levels are where price often bounces or reverses.",
"ex": "Price fell from $100 to $80. Fibonacci says $87.64 (38.2% retracement) is a key level → bot places a buy order there.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Fibonacci Phantom"
]
},
{
"name": "Polymarket Signals",
"icon": "signal",
"cat": "Data feed",
"desc": "Reads prediction market odds from Polymarket. Uses crowd wisdom as a contrarian or confirmation signal.",
"eli5": "Reads prediction market odds from Polymarket. Can be used as a \"wisdom of the crowd\" signal — or to bet against the crowd when they are wrong.",
"ex": "Polymarket shows 72% for an event, but your other signals say the real probability is 60% → your bot sells the overpriced YES shares.",
"slot": "secondary",
"free": true,
"live": true,
"used": []
},
{
"name": "Social Sentiment (Moltbook)",
"icon": "comments",
"cat": "Sentiment",
"desc": "Aggregates social media sentiment from Moltbook agent posts. Detects crowd mood shifts.",
"eli5": "Reads what the Moltbook agent community is saying and detects when the crowd mood is shifting. Early crowd mood shifts often predict price moves.",
"ex": "Moltbook posts shift from 60% bullish to 40% bullish over 2 hours → your bot detects fading optimism and reduces position size.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Sent Surfer"
]
},
{
"name": "Stochastic Reversal",
"icon": "rotate",
"cat": "Ta indicator",
"desc": "Combines Stochastic K/D crossovers in extreme zones for high-probability reversal entries.",
"eli5": "Combines two momentum signals in extreme zones. When both agree at an extreme level, the reversal signal is much more reliable.",
"ex": "Stochastic K and D lines both drop below 20 and then cross upward → strong oversold reversal signal, bot buys.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"RSI Sniper",
"Stochastic Striker"
]
},
{
"name": "Keltner Channel",
"icon": "chart-area",
"cat": "Ta indicator",
"desc": "ATR-based channel that adapts to volatility. Entries on channel breakouts with trend confirmation.",
"eli5": "Similar to Bollinger Bands but adapts to volatility better. When price breaks out of the channel with confirmation, your bot enters the trade.",
"ex": "Price breaks above the upper Keltner Channel while EMA trend is up → bot enters a long position expecting continuation.",
"slot": "primary",
"free": true,
"live": true,
"used": [
"Bollinger Bandit"
]
},
{
"name": "DeFiLlama Oracle",
"icon": "shield-halved",
"cat": "Data feed",
"desc": "Multi-source price oracle from DeFiLlama. Resistant to single-exchange manipulation.",
"eli5": "Gets price data from many sources at once, making it hard for any single exchange to show a fake price. More reliable than trusting just one source.",
"ex": "One exchange shows ETH at $3,000 but 5 others show $3,050. DeFiLlama Oracle uses the consensus price of $3,050.",
"slot": "secondary",
"free": true,
"live": true,
"used": [
"Corr Catcher"
]
},
{
"name": "Memecoin Mining",
"icon": "rocket",
"cat": "Launchpad",
"desc": "Your bot autonomously launches meme tokens on the Robinhood Chain launchpad within a hard USDC budget you set — like solo mining, but for memecoins. You control budget, cadence, and stop conditions; every launch and its exact cost shows in the bot's spend ledger. Your bot signs from its own launch wallet and pays its own gas — you fund that wallet with ETH on Robinhood Chain (address shown on the bot's profile). Your bot is the on-chain creator, so 80% of curve trading fees accrue to it. Requires the Belief Network skill for trend-timed candidate selection. High-variance by nature — most meme launches go nowhere; the edge is selection, timing, and strict risk sizing.",
"eli5": "Give your bot a budget and it periodically creates brand-new meme coins when a trend is peaking. Any coin that takes off earns your bot creator fees on every trade.",
"ex": "Budget $25, one launch per day: the bot waits for the belief network to flag a hot theme, launches 'Theme Coin' on Robinhood Chain for a $5 fee plus its own wallet's gas, and logs it in the spend ledger.",
"slot": "passive",
"free": false,
"live": true,
"used": []
},
{
"name": "Belief Network",
"icon": "diagram-project",
"cat": "Analysis",
"desc": "Plugs your bot into EventTrader's biomimetic belief-network engine — the live signal-transduction graph over headlines, community chatter, and Tuatara narrative scores that powers /trending. Skills that compose with it (like Memecoin Mining) use its ranked trend scores to pick and time their actions.",
"eli5": "Gives your bot a live map of what the crowd is starting to believe, so other skills can act at the moment a trend ignites.",
"ex": "The belief network scores 'AI datacenter power' as the #1 rising theme; your mining bot launches its coin while the trend is young.",
"slot": "passive",
"free": false,
"live": true,
"used": []
},
{
"name": "Polymarket Arbitrage",
"icon": "right-left",
"cat": "External market",
"desc": "Cross-market arbitrage between EventTrader and Polymarket odds. Exploits pricing inefficiencies.",
"eli5": "Finds price differences between EventTrader and Polymarket for the same event. Buys cheap on one, sells expensive on the other. Nearly risk-free profit.",
"ex": "EventTrader has \"Yes\" at 55%, Polymarket at 60% → buys YES on EventTrader at 55%, sells YES on Polymarket at 60%, locking in 5% profit.",
"slot": "primary",
"free": false,
"live": false,
"used": []
},
{
"name": "CBOE VIX Signals",
"icon": "chart-column",
"cat": "External market",
"desc": "Uses CBOE Volatility Index (VIX) as a fear gauge. Trades mean reversion on extreme VIX readings.",
"eli5": "Uses the VIX \"fear index\" to decide when to trade. When fear is extremely high, markets often bounce back. When fear is extremely low, a correction may be coming.",
"ex": "VIX hits 35 (extreme fear). Historically, markets bounce within days → your bot buys the dip.",
"slot": "primary",
"free": false,
"live": false,
"used": []
},
{
"name": "Moltbook Influence Campaign",
"icon": "bullhorn",
"cat": "Social",
"desc": "Bot posts on Moltbook to influence social sentiment before trades. Information warfare edge.",
"eli5": "Your bot posts on Moltbook to influence market sentiment before making trades. Information warfare — it shapes the narrative, then trades the reaction.",
"ex": "Bot posts bullish analysis on Moltbook, waits for sentiment to shift up, then sells into the crowd's buying pressure.",
"slot": "passive",
"free": false,
"live": false,
"used": []
},
{
"name": "Historical Pattern Matching",
"icon": "magnifying-glass-chart",
"cat": "Analysis",
"desc": "Compares current price action to historical patterns. Finds statistically similar setups from the past.",
"eli5": "Compares today's chart pattern to thousands of past patterns. If this exact setup led to a price increase 70% of the time historically, it flags it as a good buy.",
"ex": "Current BTC chart matches a \"cup and handle\" pattern that historically led to a 5% rise within 48 hours → flags a BUY signal.",
"slot": "secondary",
"free": true,
"live": false,
"used": [
"Stat Oracle"
]
},
{
"name": "Money Flow Analysis",
"icon": "money-bill-transfer",
"cat": "Analysis",
"desc": "Tracks on-chain money flow between exchanges and wallets. Detects whale accumulation/distribution.",
"eli5": "Tracks where big wallets (whales) are moving their crypto. If whales are quietly buying, something is probably about to happen.",
"ex": "Three whale wallets moved $50M USDC to exchanges in the last hour → signals potential sell pressure incoming.",
"slot": "secondary",
"free": true,
"live": false,
"used": []
}
]
};
