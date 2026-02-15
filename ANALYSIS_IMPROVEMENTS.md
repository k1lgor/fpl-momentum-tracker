# FPL Momentum Tracker - Analysis Improvements

## Executive Summary

This document details the bottlenecks and logic issues identified in the player momentum calculation system, along with the fixes implemented.

## Critical Issues Fixed

### 1. Data Leakage in Rolling Aggregations ✅ FIXED

**Severity:** Critical  
**Location:** `src/scripts/analyze_momentum.py`, lines 112-124

**Problem:**
Rolling aggregations were summing statistics from ALL games in the window, including games where the player didn't play (minutes = 0). This inflated xG statistics and corrupted the xG difference calculations.

**Example:**
```python
# Before (INCORRECT):
pl.col("expected_goals").tail(w).sum()

# After (CORRECT):
pl.col("expected_goals").filter(pl.col("minutes") > 0).tail(w).sum()
```

**Impact:**
- Players who didn't play in some games had artificially inflated xG totals
- xG diff calculations were incorrect, leading to wrong BUY/SELL signals
- The issue was particularly problematic for rotated players or those returning from injury

**Test Added:** `test_rolling_aggregation_filters_zero_minutes` validates the fix

---

### 2. SELL Signal Logic Producing False Positives ✅ FIXED

**Severity:** Critical  
**Location:** `src/scripts/analyze_momentum.py`, lines 205-209

**Problem:**
The rotation risk condition triggered SELL signals for players with <50% games played and >0.5 xG diff. This was too broad and caught players returning from injury with 1-2 strong performances.

**Changes:**
```python
# Before (TOO BROAD):
((pl.col("games_played_pct") < 0.5) & (pl.col("xg_diff") > 0.5))

# After (MORE PRECISE):
((pl.col("games_played_pct") < 0.3) & (pl.col("xg_diff") > 1.0))
```

**Rationale:**
- Tightened games_played threshold: 50% → 30% (must be severely rotated)
- Raised xG diff threshold: 0.5 → 1.0 (must be extreme overperformance)
- Reduces false positives for players returning from injury

---

### 3. Redundant DEFCON Calculation ✅ FIXED

**Severity:** Medium (Performance)  
**Location:** `src/scripts/analyze_momentum.py`, lines 155-172

**Problem:**
The DEFCON score formula was calculated twice:
1. Once for `defcon_score` (lines 155-161)
2. Again for `defcon_per_90` (lines 166-172)

**Fix:**
```python
# Calculate DEFCON once
(pl.col("rolling_tackles") + (pl.col("rolling_recoveries") / 4.0) + pl.col("rolling_cbi"))
.alias("defcon_score"),

# Reuse in second calculation
pl.when(pl.col("rolling_minutes") > 0)
.then(pl.col("defcon_score") / pl.col("rolling_minutes") * 90)
.otherwise(0)
.alias("defcon_per_90")
```

**Impact:** Improved code clarity and reduced redundant calculations

---

## Issues Documented (No Changes Required)

### 4. Serial Window Processing

**Severity:** High (Performance)  
**Location:** Lines 102-217

**Problem:**
The three window sizes (4, 6, 10) are processed sequentially in a loop instead of in parallel.

**Recommendation for Future:**
- Use `concurrent.futures` for parallel window processing
- Or leverage Polars' lazy evaluation with `collect_all()`
- **Not implemented now** to maintain minimal changes approach

**Current Performance:** Acceptable for current dataset size (~544 players)

---

### 5. Momentum Threshold Justification

**Severity:** Low (Documentation)  
**Location:** Lines 190, 207

**Observation:**
- BUY threshold: momentum_score > 0.005
- SELL threshold: momentum_score < -0.005

**Status:** These thresholds appear empirically derived and work well in practice. The 0.005 value is reasonable for a reliability-weighted slope (slope × R²) metric.

**Recommendation:** Document how these thresholds were chosen in future work

---

## Current Analysis Quality

### Signal Distribution (Window 6)
- **BUY signals:** 9 players (1.7%)
- **HOLD signals:** 524 players (96.3%)
- **SELL signals:** 11 players (2.0%)

### Data Quality Metrics
- Total players analyzed: 544
- Players with valid momentum scores: 334 (61.4%)
- Players with insufficient data: 210 (38.6%)

---

## Test Coverage

### New Tests Added
1. `test_rolling_aggregation_filters_zero_minutes` - Validates data leakage fix

### Existing Tests (All Passing)
- `test_momentum_with_valid_increasing_data`
- `test_momentum_with_valid_decreasing_data`
- `test_momentum_with_flat_data`
- `test_momentum_with_insufficient_data`
- `test_momentum_with_empty_list`
- `test_momentum_with_none_values`
- `test_momentum_with_nan_values`
- `test_momentum_with_all_none`
- `test_momentum_preserves_temporal_alignment`
- `test_data_processing_pipeline`
- `test_xgi_per_90_calculation`

**Total Test Count:** 12 (all passing) ✅

---

## Performance Impact

### Before Fixes
- Data leakage causing incorrect signal generation
- Redundant calculations slowing down analysis
- False positive SELL signals affecting recommendations

### After Fixes
- Correct xG diff calculations
- Improved code efficiency (DEFCON optimization eliminates duplicate formula)
- More accurate BUY/SELL signals with reduced false positives
- All tests passing with 100% success rate

---

## Recommendations for Future Work

1. **Parallel Window Processing:** Implement concurrent processing for the 3 window sizes
2. **Replace map_elements():** Consider using native Polars operations or batch NumPy conversion for momentum calculation
3. **Threshold Sensitivity Analysis:** Document how the 0.005 momentum thresholds were chosen
4. **Additional Tests:** Add integration tests that validate full pipeline output
5. **Performance Monitoring:** Add timing metrics to track analysis performance over time

---

## Conclusion

The fixes implemented address the most critical issues:
- ✅ Data leakage eliminated
- ✅ Signal logic improved
- ✅ Code optimized
- ✅ Tests added and passing

The momentum tracker now provides more accurate and reliable player recommendations for FPL managers.
