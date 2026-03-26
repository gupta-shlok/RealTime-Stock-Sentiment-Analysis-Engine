# Sentiment Patterns Research

**Project:** RealTime Stock Sentiment Analysis Engine
**Focus:** Financial sentiment aggregation, trend calculation, LLM narrative generation, sector roll-up, model normalization
**Researched:** 2026-03-26
**Overall confidence:** MEDIUM-HIGH (formulas verified via multiple sources; prompt templates are synthesized from patterns, not single canonical source)

---

## Current State (from `backend/main.py` audit)

The existing pipeline scores individual headlines using FinBERT only for bulk news tagging
(`analyze_sentiment_ensemble` calls `finbert_score` exclusively, Qwen is reserved for
`/analyze-custom`). The score formula is already correct:

```
current: score = confidence if positive, -confidence if negative, 0.0 if neutral
```

This maps FinBERT's top-label confidence to [-1, 1] but discards the other two class
probabilities. The ensemble blend is hardcoded at 60/40. The gaps to fill:

- No time-series aggregation of article scores into a stock-level trend
- No per-stock narrative endpoint
- No sector grouping or sector-level sentiment
- Full ensemble (both FinBERT + Qwen) is only used for `/analyze-custom`, not bulk tagging

---

## 1. FinBERT Output Normalization

### The Problem with the Current Approach

`finbert_score` in `main.py` uses only the winning label's confidence:

```python
result = finbert_pipe(text[:512])[0]   # returns {"label": "positive", "score": 0.87}
score = result['score'] if label == 'positive' else -result['score']
```

The `pipeline()` API returns only the top label and its softmax probability. This discards
the actual distribution. If the real probabilities are `pos=0.87, neg=0.10, neu=0.03` that
is quite different from `pos=0.87, neg=0.02, neu=0.11`, but both return `+0.87`.

### Recommended Normalization: Full Probability Extraction

Run FinBERT directly (not through the pipeline shortcut) to retrieve all three class
probabilities, then apply the standard formula from the literature (HIGH confidence —
explicitly stated in the FinBERT paper, arxiv 2306.02136, and the Prosus blog):

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
finbert_model.eval()

# FinBERT label order: {0: "positive", 1: "negative", 2: "neutral"}
FINBERT_LABELS = {0: "positive", 1: "negative", 2: "neutral"}

def finbert_full_score(text: str) -> dict:
    """
    Returns the full probability distribution and the canonical [-1,1] score.
    Formula: score = P(positive) - P(negative)
    Range: [-1, 1]; pure positive = +1, pure negative = -1, pure neutral = 0
    """
    inputs = finbert_tokenizer(
        text[:512], return_tensors="pt", truncation=True, padding=True
    )
    with torch.no_grad():
        logits = finbert_model(**inputs).logits          # shape: (1, 3)
    probs = F.softmax(logits, dim=1).squeeze()           # shape: (3,)
    p_pos = probs[0].item()
    p_neg = probs[1].item()
    p_neu = probs[2].item()
    score = p_pos - p_neg                                # canonical formula
    return {
        "score": score,          # [-1, 1]
        "p_positive": p_pos,
        "p_negative": p_neg,
        "p_neutral": p_neu,
        "confidence": max(p_pos, p_neg, p_neu),          # max-class confidence
        "uncertainty": 1 - max(p_pos, p_neg, p_neu),    # entropy proxy
    }
```

### Why P(positive) - P(negative) is Better than Pipeline Label Score

| Scenario | Pipeline score | Full-prob score | Interpretation |
|---|---|---|---|
| pos=0.87, neg=0.10, neu=0.03 | +0.87 | +0.77 | Slightly muted — neg signal present |
| pos=0.87, neg=0.02, neu=0.11 | +0.87 | +0.85 | Near-pure positive, correct |
| pos=0.48, neg=0.45, neu=0.07 | +0.48 | +0.03 | Nearly neutral — pipeline overstates |
| neg=0.70, pos=0.25, neu=0.05 | -0.70 | -0.45 | Mixed signal, pipeline overstates |

The full-prob formula is self-normalizing to [-1, 1] and embeds uncertainty naturally.
Sources: [FinBERT paper (arXiv 2306.02136)](https://arxiv.org/html/2306.02136v3), [Prosus blog](https://medium.com/prosus-ai-tech-blog/finbert-financial-sentiment-analysis-with-bert-b277a3607101)

---

## 2. Ensemble Weighting: FinBERT + Qwen

### Current State

The `/analyze-custom` endpoint uses a hardcoded `0.6 * fb_val + 0.4 * qwen_val`. This is
reasonable but not grounded in the model's output distributions.

### Recommended: Confidence-Proportional Soft Blend

Weight each model's contribution by its own reported confidence, then normalize. This
outperforms fixed weighting when one model is clearly more certain:

```python
def ensemble_score(
    fb_score: float,
    fb_confidence: float,
    qwen_score: float,
    qwen_confidence: float,
    finbert_base_weight: float = 0.6,
    qwen_base_weight: float = 0.4,
) -> float:
    """
    Confidence-proportional ensemble blend.

    The base weights encode our prior belief in each model's domain expertise
    (FinBERT is domain-trained; Qwen is generalist reasoning).
    The confidence multipliers adjust for how certain each model is on THIS input.

    Formula:
        w_fb   = base_weight_fb * confidence_fb
        w_qwen = base_weight_qwen * confidence_qwen
        score  = (w_fb * fb_score + w_qwen * qwen_score) / (w_fb + w_qwen)
    """
    w_fb = finbert_base_weight * fb_confidence
    w_q  = qwen_base_weight * qwen_confidence
    total_weight = w_fb + w_q
    if total_weight == 0:
        return 0.0
    return (w_fb * fb_score + w_q * qwen_score) / total_weight
```

### Fallback Rule

If Qwen fails to produce valid JSON (which happens — see `get_qwen_analysis` error path),
fall back to FinBERT-only. Never assign 0.0 as a fallback score; it incorrectly biases
toward neutral.

```python
def safe_ensemble(text: str) -> dict:
    fb = finbert_full_score(text)
    qwen_score, qwen_reason = get_qwen_analysis(text)
    qwen_confidence = abs(qwen_score)   # Qwen confidence is embedded in magnitude

    if qwen_confidence < 0.05:          # Qwen returned ~neutral or failed
        final_score = fb["score"]
        source = "finbert_only"
    else:
        final_score = ensemble_score(
            fb["score"], fb["confidence"],
            qwen_score, qwen_confidence
        )
        source = "ensemble"
    return {"score": final_score, "source": source, "reasoning": qwen_reason}
```

### Alternative: FinSentLLM-Style Meta-Classifier (Advanced)

For higher accuracy, extract signal features from both models and train a lightweight
logistic regression classifier on them (MEDIUM confidence — from FinSentLLM paper,
arXiv 2509.12638):

```
Features fed to meta-classifier:
  - finbert_p_positive, finbert_p_negative, finbert_p_neutral
  - finbert_margin = p_positive - max(p_negative, p_neutral)
  - finbert_entropy = -sum(p * log(p) for p in [p_pos, p_neg, p_neu])
  - qwen_score, qwen_confidence
  - l1_agreement = 1 - 0.5 * |finbert_score - qwen_score|
  - domain_flags: binary (contains "revenue", "earnings beat", "guidance raised", etc.)
```

This is overkill for a portfolio project but is the production-grade approach.

---

## 3. Article-Level to Stock-Level Score Aggregation

### Step 1: Per-Article Score (Foundation)

Each news article gets a signed score in [-1, 1] via the ensemble above. Store with
timestamp. The article score is the atomic unit everything else builds on.

### Step 2: Daily Stock Score — Confidence-Weighted Mean

Within a trading day, average all article scores for a given ticker, weighted by each
article's ensemble confidence. This prevents low-confidence near-neutral articles from
dragging down a strong signal.

Formula (HIGH confidence — from Berkeley 2024 project and arXiv 2306.02136):

```
daily_score(ticker, day) = sum(score_i * confidence_i) / sum(confidence_i)
                           for all articles i about ticker on that day
```

If no articles exist for a ticker on a given day, carry forward the previous day's score
with a decay multiplier (see Section 4).

```python
import pandas as pd

def daily_stock_scores(articles_df: pd.DataFrame) -> pd.DataFrame:
    """
    articles_df columns: ticker, date (YYYY-MM-DD), score, confidence
    Returns: ticker, date, daily_score, article_count
    """
    articles_df["weighted_score"] = articles_df["score"] * articles_df["confidence"]
    grouped = articles_df.groupby(["ticker", "date"]).agg(
        weighted_score_sum=("weighted_score", "sum"),
        confidence_sum=("confidence", "sum"),
        article_count=("score", "count"),
    ).reset_index()
    grouped["daily_score"] = grouped["weighted_score_sum"] / grouped["confidence_sum"]
    return grouped[["ticker", "date", "daily_score", "article_count"]]
```

### Step 3: Volume Weighting (Optional Enhancement)

Weight days by how many articles were published — more coverage = more reliable signal.
Use log-scaling to prevent a single high-volume day from dominating:

```python
import numpy as np

def volume_weighted_period_score(daily_df: pd.DataFrame) -> float:
    """
    daily_df columns: daily_score, article_count
    Log-volume weighting reduces the influence of high-volume outlier days.
    """
    log_counts = np.log1p(daily_df["article_count"])   # log(1 + count)
    return (daily_df["daily_score"] * log_counts).sum() / log_counts.sum()
```

---

## 4. Sentiment Trend Calculation

### Time Window Recommendations

Based on research on news sentiment half-life in financial markets (MEDIUM confidence):

| Window | Use Case | Implementation |
|---|---|---|
| 24h | Real-time feed display, intraday signals | Raw daily score |
| 7d | Short-term momentum, weekly trend | EMA with span=5 (trading days) |
| 30d | Narrative context, sector comparison | EMA with span=20 (trading days) |

Avoid using simple rolling mean for sentiment — it treats a 30-day-old article identically
to today's article. Use EMA.

### EMA Implementation with Pandas

```python
def compute_sentiment_trend(daily_scores: pd.Series, spans: list[int] = [5, 20]) -> pd.DataFrame:
    """
    daily_scores: pd.Series indexed by date, values in [-1, 1]
    Returns DataFrame with original scores plus EMA columns.

    span=5  ~ 7-day trend (5 trading days, alpha = 2/6 = 0.333)
    span=20 ~ 30-day trend (20 trading days, alpha = 2/21 = 0.095)

    pandas ewm() uses: alpha = 2 / (span + 1)
    Each observation's weight decays as: w_i = alpha * (1 - alpha)^(n-1-i)
    """
    result = pd.DataFrame({"raw_score": daily_scores})
    for span in spans:
        col_name = f"ema_{span}d"
        result[col_name] = daily_scores.ewm(span=span, adjust=True).mean()
    return result
```

### Recency Decay for Article-Level Aggregation (Alternative to EMA)

When aggregating articles within a window (e.g., past 7 days), apply exponential decay
based on hours since publication rather than waiting for daily buckets. This is useful
for real-time endpoints.

```python
from datetime import datetime, timezone
import math

def recency_weight(published_at: datetime, half_life_hours: float = 24.0) -> float:
    """
    Exponential decay weight for a single article.

    Formula: w = exp(-lambda * t)
    where:
        lambda = ln(2) / half_life_hours   (decay rate)
        t      = hours since publication

    half_life_hours=24 means an article published 24h ago weighs half as much
    as one published now. Published 48h ago weighs 0.25x.

    Recommended half-lives:
        24h  — for 7-day windows (aggressive decay, recency-focused)
        72h  — for 30-day windows (gentler, allows weekly story arcs)
    """
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    hours_ago = (now - published_at).total_seconds() / 3600
    decay_rate = math.log(2) / half_life_hours
    return math.exp(-decay_rate * hours_ago)

def recency_weighted_score(articles: list[dict], half_life_hours: float = 24.0) -> float:
    """
    articles: list of {"score": float, "confidence": float, "published_at": datetime}
    Combined recency + confidence weighting.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for article in articles:
        w = recency_weight(article["published_at"], half_life_hours)
        w *= article["confidence"]       # confidence modulates recency weight
        weighted_sum += w * article["score"]
        total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0.0
```

### Trend Direction Signal

Beyond the raw score, compute a trend direction for UI display (e.g., "improving" /
"worsening" / "stable"):

```python
def sentiment_trend_direction(ema_5d: pd.Series, threshold: float = 0.05) -> str:
    """
    Compare latest EMA to 5-day-ago EMA to determine direction.
    threshold: minimum change to declare a directional trend (avoids noise).
    """
    if len(ema_5d) < 6:
        return "insufficient_data"
    delta = ema_5d.iloc[-1] - ema_5d.iloc[-6]
    if delta > threshold:
        return "improving"
    elif delta < -threshold:
        return "worsening"
    return "stable"
```

---

## 5. Sector-Level Aggregation

### GICS Sector Mapping (S&P 500 — 11 Sectors)

GICS is the standard (HIGH confidence — S&P Dow Jones Indices official classification):

```python
GICS_SECTORS = {
    "Information Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "AMD", "INTC", "IBM", "CRM", "ORCL", "AMAT"],
    "Communication Services": ["GOOG", "GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS"],
    "Consumer Discretionary": ["AMZN", "TSLA", "MCD", "NKE", "SBUX", "TGT", "HD", "LOW", "BKNG"],
    "Consumer Staples":       ["COST", "PG", "KO", "PEP", "WMT", "PM", "MO", "CL", "GIS"],
    "Financials":             ["BRK-B", "JPM", "BAC", "GS", "MS", "WFC", "BX", "AXP", "C"],
    "Healthcare":             ["LLY", "JNJ", "UNH", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY"],
    "Industrials":            ["BA", "HON", "UPS", "CAT", "DE", "LMT", "RTX", "GE", "MMM"],
    "Energy":                 ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "OXY", "VLO", "MPC"],
    "Materials":              ["LIN", "APD", "SHW", "FCX", "NEM", "NUE", "DOW", "DD", "PPG"],
    "Real Estate":            ["PLD", "AMT", "EQIX", "CCI", "PSA", "SPG", "O", "WELL", "DLR"],
    "Utilities":              ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PCG", "ED"],
}

# Reverse map: ticker -> sector (build once at startup)
TICKER_TO_SECTOR = {
    ticker: sector
    for sector, tickers in GICS_SECTORS.items()
    for ticker in tickers
}
```

For dynamic lookup across all 500 tickers, use yfinance info (MEDIUM confidence):

```python
import yfinance as yf

def get_sector(ticker: str) -> str:
    """Fallback: fetch sector from yfinance when ticker not in static map."""
    try:
        return yf.Ticker(ticker).info.get("sector", "Unknown")
    except Exception:
        return "Unknown"
```

### Stock-Level to Sector-Level Aggregation

Two viable approaches — use equal weight for portfolio projects (MEDIUM confidence,
supported by RavenPack research and Nature 2024 study):

**Equal Weight (recommended for portfolio project):**
Every stock in a sector contributes equally regardless of market cap.
This is preferred because small-cap stocks are often more sentiment-sensitive than
large-caps, so market-cap weighting underweights the most sentiment-reactive names.

```python
def sector_sentiment(
    stock_scores: dict[str, float],   # {ticker: score_in_[-1,1]}
    ticker_to_sector: dict[str, str],
) -> dict[str, dict]:
    """
    Aggregate stock-level scores to sector level using equal weighting.

    Returns {sector_name: {"score": float, "stock_count": int, "contributing_tickers": list}}
    """
    from collections import defaultdict
    sector_buckets = defaultdict(list)
    for ticker, score in stock_scores.items():
        sector = ticker_to_sector.get(ticker, "Unknown")
        if sector != "Unknown":
            sector_buckets[sector].append((ticker, score))

    result = {}
    for sector, pairs in sector_buckets.items():
        scores = [s for _, s in pairs]
        result[sector] = {
            "score": sum(scores) / len(scores),
            "stock_count": len(scores),
            "contributing_tickers": [t for t, _ in pairs],
        }
    return result
```

**Market-Cap Weight (if you add market cap data):**

```python
def sector_sentiment_mcap_weighted(
    stock_scores: dict[str, float],
    market_caps: dict[str, float],    # {ticker: market_cap_in_usd}
    ticker_to_sector: dict[str, str],
) -> dict[str, float]:
    from collections import defaultdict
    sector_score_num = defaultdict(float)
    sector_mcap_den  = defaultdict(float)
    for ticker, score in stock_scores.items():
        sector = ticker_to_sector.get(ticker, "Unknown")
        mcap   = market_caps.get(ticker, 0)
        if sector != "Unknown" and mcap > 0:
            sector_score_num[sector] += score * mcap
            sector_mcap_den[sector]  += mcap
    return {
        s: sector_score_num[s] / sector_mcap_den[s]
        for s in sector_score_num
        if sector_mcap_den[s] > 0
    }
```

### Sector Sentiment Label Thresholds

```python
def sector_label(score: float) -> str:
    """
    Sectors are more stable than individual stocks; use tighter thresholds.
    A sector score of +0.1 is meaningful; +0.15 is significant.
    """
    if score >= 0.15:  return "Strongly Bullish"
    if score >= 0.05:  return "Mildly Bullish"
    if score <= -0.15: return "Strongly Bearish"
    if score <= -0.05: return "Mildly Bearish"
    return "Neutral"
```

---

## 6. LLM Narrative Generation Prompts

### Design Principles

From the literature (MEDIUM confidence — synthesized from multiple 2024-2025 sources):

1. Give Qwen a **role** and a **format constraint** in the system prompt.
2. Provide headlines with their scores — don't ask Qwen to re-score, ask it to explain
   what the scores mean collectively.
3. Request a **fixed output schema** (JSON or structured text) to make parsing reliable.
4. Use Chain-of-Thought for narrative generation, not for classification (CoT helps
   generate richer explanations but increases token usage and latency).
5. Cap total input at ~600 tokens for Qwen2.5-1.5B. Beyond this, the model's context
   window fills and quality degrades noticeably.

### Template 1: Per-Stock Narrative (Primary Use Case)

```python
STOCK_NARRATIVE_SYSTEM = """You are a concise financial analyst assistant.
Given a list of recent news headlines and their sentiment scores for a stock,
write a brief market narrative. Be factual, specific, and avoid speculation.
Respond ONLY with valid JSON — no preamble, no explanation outside the JSON."""

STOCK_NARRATIVE_USER_TEMPLATE = """Stock: {ticker}
Period: {period}
Overall sentiment score: {overall_score:.2f} ({overall_label})

Recent headlines (score: -1.0=very bearish to +1.0=very bullish):
{headlines_block}

Respond with ONLY this JSON:
{{
  "summary": "2-3 sentence narrative explaining why sentiment is {overall_label}",
  "key_drivers": ["driver 1", "driver 2", "driver 3"],
  "risk_flag": "one sentence about the biggest uncertainty or risk, or null if none"
}}"""

def format_headlines_block(articles: list[dict], max_articles: int = 8) -> str:
    """
    articles: [{"title": str, "score": float, "published_at": str}, ...]
    Sort by absolute score (most opinionated first) then take top N.
    """
    sorted_articles = sorted(articles, key=lambda x: abs(x["score"]), reverse=True)
    lines = []
    for a in sorted_articles[:max_articles]:
        sign = "+" if a["score"] >= 0 else ""
        lines.append(f'  [{sign}{a["score"]:.2f}] "{a["title"]}" ({a["published_at"]})')
    return "\n".join(lines)

def build_stock_narrative_prompt(
    ticker: str,
    articles: list[dict],
    overall_score: float,
    period: str = "last 7 days",
) -> list[dict]:
    """Returns messages list for Qwen apply_chat_template."""
    headlines_block = format_headlines_block(articles)
    overall_label = label_from_score(overall_score)
    user_content = STOCK_NARRATIVE_USER_TEMPLATE.format(
        ticker=ticker,
        period=period,
        overall_score=overall_score,
        overall_label=overall_label,
        headlines_block=headlines_block,
    )
    return [
        {"role": "system", "content": STOCK_NARRATIVE_SYSTEM},
        {"role": "user",   "content": user_content},
    ]
```

### Template 2: Sector Narrative

```python
SECTOR_NARRATIVE_USER_TEMPLATE = """Sector: {sector}
Period: {period}
Sector sentiment score: {sector_score:.2f} ({sector_label})
Stocks analyzed: {stock_count}

Top movers in this sector:
{movers_block}

Write a 2-3 sentence sector narrative explaining the dominant themes.
Respond with ONLY this JSON:
{{
  "summary": "2-3 sentence sector narrative",
  "dominant_theme": "single phrase (e.g., 'AI infrastructure spending', 'interest rate pressure')",
  "outliers": ["ticker with unusual sentiment vs sector if any"]
}}"""

def build_sector_narrative_prompt(
    sector: str,
    sector_score: float,
    stock_sentiments: dict[str, float],   # {ticker: score}
    period: str = "last 7 days",
) -> list[dict]:
    # Sort stocks by score to show strongest signals
    sorted_stocks = sorted(stock_sentiments.items(), key=lambda x: x[1], reverse=True)
    movers_lines = []
    for ticker, score in sorted_stocks[:6]:
        sign = "+" if score >= 0 else ""
        movers_lines.append(f"  {ticker}: {sign}{score:.2f}")
    movers_block = "\n".join(movers_lines)

    user_content = SECTOR_NARRATIVE_USER_TEMPLATE.format(
        sector=sector,
        period=period,
        sector_score=sector_score,
        sector_label=sector_label(sector_score),
        stock_count=len(stock_sentiments),
        movers_block=movers_block,
    )
    return [
        {"role": "system", "content": STOCK_NARRATIVE_SYSTEM},
        {"role": "user",   "content": user_content},
    ]
```

### Few-Shot Addendum (Template 3: With Examples)

For higher output quality at the cost of more tokens, prepend a completed example.
Only use this if generation quality is poor without it (adds ~200 tokens per call):

```python
FEW_SHOT_EXAMPLE = """
Example:
Stock: NVDA
Overall sentiment: +0.72 (Bullish)
Headlines:
  [+0.91] "Nvidia beats Q3 earnings, data center revenue up 112% YoY" (2 days ago)
  [+0.85] "Jensen Huang signals strong AI chip demand through 2025" (3 days ago)
  [-0.34] "Antitrust scrutiny intensifies in EU over Nvidia market dominance" (5 days ago)

Response:
{
  "summary": "NVDA sentiment is strongly bullish driven by exceptional earnings and sustained data center demand. The AI infrastructure build-out narrative remains intact, with management commentary reinforcing strong forward guidance. The sole bearish signal is regulatory — EU antitrust review — which is a tail risk rather than a near-term earnings threat.",
  "key_drivers": ["Data center revenue beat", "AI chip demand guidance", "Strong YoY growth"],
  "risk_flag": "EU antitrust investigation could constrain market share in European cloud markets."
}
"""
```

### Qwen Generation Parameters for Narratives

For narrative generation (not classification), adjust generation settings:

```python
NARRATIVE_GENERATION_KWARGS = {
    "max_new_tokens": 250,        # narratives need more space than single-label JSON
    "temperature": 0.3,           # slightly higher than 0.1 to allow natural language variety
    "do_sample": True,            # needed when temperature > 0
    "top_p": 0.9,                 # nucleus sampling — filters unlikely tokens
    "repetition_penalty": 1.1,    # reduces repetitive phrasing common in small models
    "pad_token_id": qwen_tokenizer.eos_token_id,
}
```

Note: The current `get_qwen_analysis` uses `do_sample=False` and `temperature=0.1`,
which is correct for structured JSON classification. For narrative generation,
increase temperature to 0.3 and enable sampling to produce more natural prose.

---

## 7. End-to-End Pipeline Design

### Data Flow

```
[Yahoo Finance news fetch]
        |
        v
[Per-article: finbert_full_score() + get_qwen_analysis()]
        |
        v
[Store: {ticker, headline, score, confidence, published_at, p_pos, p_neg, p_neu}]
        |
        +------------------------+------------------------+
        v                        v                        v
[daily_stock_scores()]   [recency_weighted_score()]  [sector aggregation]
        |                        |                        |
        v                        v                        v
[compute_sentiment_trend()]  [24h score]         [sector_sentiment()]
[EMA 5d + 20d]                                           |
        |                                                 v
        +--------------------> [Qwen narrative generation]
                                        |
                                        v
                              [/sentiment-trends endpoint]
                              [/stock-narrative/{ticker}]
                              [/sector-sentiment endpoint]
```

### New Endpoints to Add

```
GET /sentiment-trends?ticker=NVDA&window=7d
  Returns: {ticker, dates[], raw_scores[], ema_5d[], ema_20d[], trend_direction}

GET /stock-narrative/{ticker}
  Returns: {ticker, overall_score, label, summary, key_drivers, risk_flag, articles_analyzed}

GET /sector-sentiment
  Returns: {sector_name: {score, label, stock_count, narrative}, ...}

GET /sector-sentiment/{sector}
  Returns: full detail for one sector including per-stock breakdown
```

---

## 8. Implementation Notes and Pitfalls

### Pitfall 1: FinBERT Headline vs Full-Article Truncation

FinBERT is fine-tuned on Financial PhraseBank sentences (short, structured). It performs
best on headlines and single sentences. Truncating a 500-word article to 512 tokens
produces worse results than running FinBERT on individual sentences and averaging.
Recommendation: always pass headlines to FinBERT, not full article bodies.

### Pitfall 2: Recency Decay Found Ineffective in One Study

The Berkeley 2024 project found that decayed historical sentiment did not improve
stock price prediction. This is important context: recency decay is useful for
display/aggregation purposes (showing what the market thinks now), but should not
be treated as a predictive feature. The goal here is descriptive, not predictive,
so decay remains appropriate.

### Pitfall 3: Small Qwen2.5-1.5B Context for Multi-Article Prompts

Qwen2.5-1.5B has a 32K token context window, but quality degrades significantly for
longer prompts on the 1.5B parameter model. Keep the headlines block under 8 items.
If a stock has 20+ articles in a period, pre-filter to the highest absolute-score
articles before passing to Qwen.

### Pitfall 4: Sector Aggregation with Thin Coverage

For the current 15 tickers in `selected_symbols`, most GICS sectors will have 1-3
tickers each. A single-ticker sector score is not meaningful as a "sector" signal.
Display sector sentiment only when `stock_count >= 3`. Flag thinner sectors.

### Pitfall 5: Neutral Score Inflation

FinBERT has a known tendency to classify ambiguous financial text as neutral. If
your dataset shows more than 60% neutral across all articles, the `analyze_sentiment_ensemble`
function (currently FinBERT-only for bulk) is likely over-classifying as neutral.
Use the full-probability formula (Section 1) and check if `p_positive + p_negative > 0.4`
before labeling as neutral.

---

## 9. Confidence Assessment

| Area | Confidence | Source |
|---|---|---|
| FinBERT normalization formula (P_pos - P_neg) | HIGH | Stated explicitly in FinBERT paper (arXiv 1908.10063) and arXiv 2306.02136 |
| EMA/EWMA for sentiment smoothing | HIGH | Pandas documentation + financial research consensus |
| Daily confidence-weighted aggregation | HIGH | Berkeley 2024 project + arXiv 2306.02136 |
| GICS 11-sector structure | HIGH | S&P Dow Jones official GICS documentation |
| Equal-weight preferred over market-cap for sentiment | MEDIUM | Nature 2024 study on sentiment aggregation; RavenPack methodology |
| Recency decay half-life recommendations (24h/72h) | MEDIUM | General EWM theory applied to news; limited financial-specific benchmarks |
| Qwen2.5 narrative prompt templates | MEDIUM | Synthesized from 2024-2025 prompting literature; not benchmarked on this specific use case |
| FinSentLLM meta-classifier approach | MEDIUM | arXiv 2509.12638; requires labeled training data not available here |
| Sector label thresholds (0.05/0.15) | LOW | Heuristic; no published benchmark for these specific values |

---

## Sources

- [FinBERT: Financial Sentiment Analysis with BERT (arXiv 1908.10063)](https://arxiv.org/abs/1908.10063)
- [FinBERT Application for Stock Movement Prediction (arXiv 2306.02136)](https://arxiv.org/html/2306.02136v3)
- [ProsusAI/finbert — Hugging Face](https://huggingface.co/ProsusAI/finbert)
- [FinSentLLM: Multi-LLM Ensemble for Financial Sentiment (arXiv 2509.12638)](https://arxiv.org/html/2509.12638)
- [Qwen2.5-1.5B-Instruct — Hugging Face](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [Sentiment Analysis for Financial Markets — UC Berkeley MIDS 2024](https://www.ischool.berkeley.edu/projects/2024/sentiment-analysis-financial-markets)
- [Methods for Aggregating Investor Sentiment from Social Media — Nature/Humanities and Social Sciences Communications 2024](https://www.nature.com/articles/s41599-024-03434-2)
- [S&P 500 RavenPack AI Sentiment Indices Methodology — S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-500-rvnpck-ai-sentiment-indices.pdf)
- [Global Industry Classification Standard — Wikipedia](https://en.wikipedia.org/wiki/Global_Industry_Classification_Standard)
- [GICS Official Standard — S&P/MSCI](https://www.spglobal.com/spdji/en/landing/topic/gics/)
- [Construction of Market Sentiment Indices Using News Sentiment — RavenPack](https://www.ravenpack.com/research/construction-market-sentiment-indices-using-news-sentiment/)
- [Large Language Models in Equity Markets — PMC/Frontiers in AI 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12421730/)
- [pandas ewm() documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html)
- [Exponentially Weighted Moving Models — Stanford/Boyd (arXiv 2404.08136)](https://arxiv.org/html/2404.08136v1)
- [Stock Price Prediction with FinBERT-Enhanced Sentiment and SHAP — MDPI 2025](https://www.mdpi.com/2227-7390/13/17/2747)
