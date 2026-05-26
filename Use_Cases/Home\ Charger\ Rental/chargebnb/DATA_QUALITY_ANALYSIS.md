# ChargeBnB Data Quality & Quantity Analysis

**Date:** May 16, 2026  
**Status:** ⚠️ CRITICAL GAPS IDENTIFIED

---

## Executive Summary

The ChargeBnB project has **significant data gaps** that severely limit the effectiveness of the SARIMAX demand model and pricing optimization. While the infrastructure (clustering, pricing engine) is solid, the underlying data is **too sparse, static, and incomplete** to support reliable demand forecasting.

### Key Findings at a Glance

| Metric | Current | Required | Gap |
|--------|---------|----------|-----|
| **Charging Events** | 558 | 50K-100K | ❌ 99% under-resourced |
| **Time Coverage** | 9 days | 6-12 months | ❌ 98% under-resourced |
| **Charger Data** | 262 chargers | 1000+ | ❌ 74% incomplete |
| **Geographic Coverage** | 66% of metro | 100% | ❌ Uneven |
| **Pricing Data** | 196/262 (75%) | 100% | ❌ 25% missing |
| **Model Training Data** | ~50 obs/cluster | 50+ required | ⚠️ Borderline |

---

## Detailed Analysis by Dataset

### 1️⃣ **EV Charging Events Dataset** (CRITICAL)

**File:** `data/ml_ev_charging_dataset.csv`  
**Current State:** 558 events across 9 calendar days (Apr 18-28, 2025)

#### Problems:
- **Temporal Sparsity:** Only 2 active days out of 11 calendar days (~18% data collection rate)
- **Insufficient Volume:** 62 events/day avg → SARIMAX needs ≥100-200 events/day minimum
- **No Historical Data:** Single 9-day snapshot, no seasonality, no trends visible
- **Raw Events, Not Aggregates:** Data is raw station visits, not aggregated daily demand per suburb
- **Limited Stations:** Only 8 unique stations tracked (should be 50+ for meaningful clustering)

#### Why This Matters:
```
SARIMAX Model Requirements:
- Need: 6-12 months of DAILY demand aggregates (not raw events)
- Format: Daily demand per suburb/cluster over time
- Minimum: 50+ time-series observations per cluster
- Current: ~558 events = ~6 aggregate data points per cluster (insufficient)
```

#### Impact on Model:
- ❌ Cannot detect seasonal patterns (only 9 days of data)
- ❌ Cannot validate AR/MA coefficients (insufficient observations)
- ❌ Fallback to rule-based multiplier (0.80–1.20 per time band)
- ❌ Confidence score permanently low (fallback: 0.50)

#### Recommendations:
1. **Collect continuous event data** for 6-12 months (Jan 2024 - Dec 2024 minimum)
2. **Aggregate to daily demand** by suburb/cluster/hour of day
3. **Target 10K-50K events minimum** (achievable with 5-10 active charger networks)
4. **Add metadata:** duration, user type, vehicle model, pricing tier

---

### 2️⃣ **Charger Information Database** (HIGH)

**File:** `backend/data/charger_info_mel.csv`  
**Current State:** 262 chargers, multiple missing fields

#### Problems:
| Field | Missing | % | Issue |
|-------|---------|---|-------|
| Usage Cost | 66 | 25.2% | Pricing unavailable for 1/4 of chargers |
| Postal Code | 43 | 16.4% | Cannot aggregate by postcode/region |
| Latitude/Longitude | 34 | 13.0% | Map visualization incomplete |
| Suburb | 16 | 6.1% | Cannot join with clustering data |
| Power Rating | 4 | 1.5% | Cannot match charger specs |

- **Coverage Gap:** 262 chargers vs. 1000+ in Melbourne metro = **74% incomplete**
- **Data Quality:** Inconsistent formatting (e.g., "75, 22" kW; mixed states "VIC" vs "AU-VIC")
- **Redundancy:** Only 196 unique suburbs covered, but clustering has 349 suburbs
- **No Dynamic Data:** Charger availability, utilization, downtime unknown

#### Why This Matters:
- Cannot accurately price chargers missing cost data (fallback to base price)
- Geographic recommendations incomplete (13% missing coords)
- Charger specs unknown for 1.5% (power matching, connector types unclear)

#### Recommendations:
1. **Fill missing fields:**
   - Scrape/API from ChargeFox, JOLT, bp pulse official databases
   - Interpolate missing postcodes from addresses
   - Calculate missing lat/lng from address geocoding
2. **Expand coverage:** Add all public chargers (target 1000+)
3. **Add dynamic fields:**
   - Occupancy rate (live or historical)
   - Downtime/maintenance schedule
   - Peak usage hours
   - User ratings (if available)

---

### 3️⃣ **Temporal Data Distribution** (CRITICAL)

**File:** `data/ml_ev_charging_dataset.csv`  
**Current State:** Sparse, inconsistent daily coverage

#### Problems:
- **2 active days out of 11** calendar days (18% collection rate)
- **9 days with zero events** – data collection incomplete
- **Inconsistent daily volume:** No baseline for what "normal" demand is
- **No hourly disaggregation:** Time-of-day patterns unknown

#### Current Data Timeline:
```
Apr 18, 2025: 279 events
Apr 19-27, 2025: 0 events (gap)
Apr 28, 2025: 279 events
```

#### Why This Matters:
- **Time-series modeling impossible** with 2 disconnected data points
- **SARIMAX enforces stationarity** – cannot learn from gaps
- **Seasonal decomposition fails** (no year-over-year or month-over-month data)
- **Peak hour detection fails** (need consistent intra-day data)

#### Recommendations:
1. **Implement continuous data collection pipeline**
   - Daily aggregation: Sum of charging events per suburb
   - Hourly disaggregation: Events by time-of-day bucket
   - Weekly/monthly rollups for trend detection
2. **Backfill historical data:**
   - Request historical EV charging data from Victoria's transport authority
   - Use public APIs (ChargePoint, PlugShare historical data if available)
   - Synthesize plausible demand from EV registration trends
3. **Target timeline:** Minimum 6 months continuous (Jan-Jun 2024 or similar)

---

### 4️⃣ **Geographic Coverage** (MEDIUM)

**Files:** `backend/data/Co-oridnates.csv`, `backend/data/clustered_suburbs.csv`, `backend/data/charger_info_mel.csv`

#### Problems:
- **197 suburbs with coordinates** vs. **300+ Melbourne metro suburbs** = 66% coverage
- **196 suburbs in charger database** vs. **349 in clustering output** = incomplete
- **Coordinate data:** 24/198 missing lat/lng (12% incomplete)
- **Mismatch:** Events span 12 suburbs, clustering includes 349, chargers span 196

#### Coverage Gaps by Region:
- ✅ Central Melbourne: Good (CBD, inner suburbs)
- ⚠️ Regional: Limited (Geelong, Ballarat data missing)
- ❌ Far suburbs: Missing (100km+ from CBD)

#### Why This Matters:
- **Pricing accuracy varies by region** – rural/regional chargers may have different demand
- **Market expansion unknown** – cannot forecast growth outside current coverage
- **Clustering invalid for unmapped suburbs** – 150+ suburbs have no charger/coordinate data
- **Map visualization incomplete** (13% chargers have no coordinates)

#### Recommendations:
1. **Geocode missing addresses:**
   - Use Google Maps API or OpenStreetMap geocoding
   - Fill 34 missing charger coordinates
   - Fill 24 missing suburb coordinates
2. **Expand to Greater Melbourne (350+ suburbs):**
   - Include Geelong, Ballarat, Bendigo regions (growing EV markets)
   - Partner with regional charging networks
3. **Validate clustering on full dataset:**
   - Re-run KMeans with complete geographic coverage
   - Create regional pricing tiers

---

### 5️⃣ **External Feature Data** (MEDIUM)

**Files:** `data/Suburb_Population.csv`, `data/Info_for_PCZ.csv`, `data/vehicle_registrations.csv`, `data/road_congestion.csv`

#### Dataset Quality:

| Dataset | Records | Coverage | Issue |
|---------|---------|----------|-------|
| Population | 350 | 100% | ✅ Complete, static (2021 census) |
| Dwellings/Income | 350 | 98% | ⚠️ 7-13 missing per field, 2-3 years old |
| EV Registrations | 594 | 200 postcodes | ❌ STATIC snapshot, not time-series |
| Congestion | 4706 SCATS sites | ~70% metro | ⚠️ Unclear if daily/hourly aggregates |

#### Problems:

**EV Registration Data (STATIC):**
- Only 1,596 total EVs across all postcodes (avg 8 EVs/postcode)
- **Single snapshot in time** – no trend data to forecast growth
- Missing: EV growth rate, make/model distribution, adoption by suburb
- Cannot explain demand changes over time (EV registrations growing ~30%/year in Australia)

**Congestion Data (UNCLEAR FORMAT):**
- 4,706 SCATS (traffic detection) sites with 96-column volume data
- Unclear if V00-V95 represent hourly volumes or 15-min intervals
- Not directly linkable to charging demand (traffic ≠ charging need)
- Useful feature: correlate congestion with charger usage (peak hours)

**Population/Dwelling (STATIC):**
- 2021 Census data (5 years old by 2026)
- Cannot capture suburb growth, demographic shifts
- Useful for clustering but not for temporal forecasting

#### Why This Matters:
- **SARIMAX exogenous features are STATIC** – don't capture time trends
- **Cannot forecast growth** in EV adoption or charging demand
- **Congestion feature unclear** – may not be directly predictive
- **Seasonality features missing:**
  - School holidays (affects demand)
  - Weather patterns (rain, cold → more charging)
  - Sporting events, holidays (demand spikes)
  - Fuel/electricity price trends

#### Recommendations:
1. **Create time-series EV registration data:**
   - Collect monthly EV registrations by postcode (2022-2026)
   - Track growth trends, market saturation
   - Use to forecast future demand
2. **Clarify congestion data format:**
   - Document V00-V95 column meanings (hourly? 15-min?)
   - Validate correlation with actual charging events
   - Create daily/hourly aggregates if raw intervals
3. **Add seasonal/contextual features:**
   - School term calendar
   - Weather data (temperature, rainfall)
   - Public holidays, events
   - Fuel/electricity prices
4. **Source updated census data:**
   - 2026 Census when available
   - Interim population estimates by ABS
   - Target age 25-55 (more likely to own EVs)

---

## Data Gaps Summary Table

### Quantity Gaps

| Category | Current | Target | Priority |
|----------|---------|--------|----------|
| Charging events | 558 | 50K-100K | 🔴 CRITICAL |
| Days of data | 9 | 180-365 | 🔴 CRITICAL |
| Chargers tracked | 262 | 1000+ | 🟠 HIGH |
| Suburbs covered | 197 coords | 350+ | 🟠 HIGH |
| Time coverage | 2 active days | Daily continuous | 🔴 CRITICAL |
| Charger pricing data | 196/262 | 262/262 | 🟠 MEDIUM |

### Quality Gaps

| Issue | Impact | Fix Priority |
|-------|--------|-------------|
| Sparse time-series | SARIMAX unreliable | 🔴 CRITICAL |
| Missing suburb/coords | Map/pricing incomplete | 🟠 HIGH |
| No hourly breakdown | Peak hour detection fails | 🟠 HIGH |
| Static EV registration | Cannot forecast growth | 🟠 HIGH |
| Inconsistent data formats | Fuzzy matching required | 🟡 MEDIUM |
| No occupancy data | Cannot detect bottlenecks | 🟡 MEDIUM |

---

## Data Improvement Roadmap

### Phase 1: Immediate (Week 1-2) 🔴
1. **Fill missing charger data:**
   - Geocode 34 missing charger coordinates
   - Fill 66 missing usage costs (API scrape or estimate from region)
   - Fix 43 missing postal codes
   - **Effort:** 4-6 hours
   - **Impact:** 25% improvement in charger completeness

2. **Document time-series gaps:**
   - Identify why April 19-27 has no data
   - Establish data collection protocol
   - **Effort:** 2-3 hours
   - **Impact:** Baseline for data quality improvement

### Phase 2: Short-term (Week 3-8) 🟠
1. **Backfill 6 months of charging data:**
   - Contact Victoria's EV charging data provider (if public)
   - Request historical data from major networks (JOLT, bp pulse, ChargeFox)
   - Aggregate to daily demand per suburb
   - **Effort:** 2-4 weeks
   - **Impact:** 90x increase in data volume, SARIMAX becomes viable

2. **Expand charger database:**
   - Web scrape / API integrate all Melbourne chargers
   - Target 800-1000 chargers
   - **Effort:** 1-2 weeks
   - **Impact:** 3-4x coverage improvement, better geographic representation

3. **Create time-series EV registration data:**
   - Monthly EV registrations by postcode (2022-2026)
   - Calculate growth trends
   - **Effort:** 1 week (if data available)
   - **Impact:** Enable growth forecasting

### Phase 3: Medium-term (Week 9-16) 🟡
1. **Implement continuous data pipeline:**
   - Daily aggregation of charging events
   - Hourly bucketing for time-of-day patterns
   - Automated data validation & quality checks
   - **Effort:** 2-3 weeks
   - **Impact:** Reliable, ongoing data stream

2. **Add contextual features:**
   - School term calendar
   - Weather data (temperature, rainfall)
   - Fuel/electricity prices
   - Public holidays, events
   - **Effort:** 1-2 weeks
   - **Impact:** Improved demand prediction (10-20% accuracy gain)

3. **Occupancy & utilization tracking:**
   - Partner with charger networks for real-time availability
   - Track downtime, maintenance windows
   - Calculate utilization rates
   - **Effort:** 2-3 weeks (data sharing agreements)
   - **Impact:** Enable capacity planning, dynamic pricing

---

## Quick Wins: Data Improvements with Minimal Effort

| Task | Effort | Impact | Steps |
|------|--------|--------|-------|
| Fill charger coordinates | 2 hrs | 13% → 100% coverage | Geocoding API + manual fixes |
| Fill charger costs | 2 hrs | 75% → 100% coverage | Regional average + web scrape |
| Document gaps | 1 hr | ✅ Baseline | Create data quality checklist |
| Fix address formats | 2 hrs | 95% → 99% cleanliness | Regex standardization |
| Add data collection date | 30 min | ✅ Tracking | Add timestamp to pipelines |
| **Total:** | **7.5 hrs** | **+30% quality** | **Doable this sprint** |

---

## Synthetic Data Strategy (Interim Workaround)

**Until real data is available,** consider synthetic demand generation:

```python
# Pseudo-code: Generate synthetic demand
for suburb in suburbs:
    base_demand = ev_count[suburb] * 0.5  # ~50% charge weekly
    for hour in hours:
        hourly_demand = base_demand * peak_multiplier[hour] * weekday_factor
        for day in days:
            daily_demand += hourly_demand + random_noise()
```

**Rationale:**
- Ground truth in EV registration counts per suburb
- Peak hour patterns from transportation research
- Realistic seasonality + random variation
- Use to train SARIMAX, validate on real data later

**Limitations:**
- Not suitable for production pricing (client-facing)
- Good for stress-testing, backtesting model robustness
- Must be clearly labeled as synthetic

---

## Recommended Data Sources

### Free/Public
- **Australian Bureau of Statistics (ABS):** EV registrations, population, census
- **Victoria's Datavic portal:** Public sector datasets, traffic, transport
- **OpenStreetMap:** Coordinates, address geocoding
- **Google Maps API:** Geocoding (500K free queries/month)
- **OpenWeather:** Historical weather data (free tier available)

### Commercial/Partnership
- **JOLT, bp pulse, ChargeFox:** Direct partnerships for charger usage data
- **HERE Maps:** Real-time traffic/congestion data (paid)
- **Uber/Google Mobility Data:** Aggregated movement patterns
- **EV charging networks:** Occupancy, reservation data

---

## Success Criteria

### By End of Phase 1 (2 weeks):
- [ ] All charger data fields ≥95% complete
- [ ] Data collection protocol documented
- [ ] 6+ months of historical data sourced

### By End of Phase 2 (8 weeks):
- [ ] 50K+ charging events collected
- [ ] SARIMAX model confidence score >0.70 (up from 0.50 fallback)
- [ ] 800+ chargers in database
- [ ] Geographic coverage >85%

### By End of Phase 3 (16 weeks):
- [ ] Daily continuous data pipeline operational
- [ ] Seasonal patterns visible in time-series
- [ ] Pricing model accuracy ±15% (from current ±30%)
- [ ] Demand forecasting enabled for 6-month horizon

---

## Conclusion

**The ChargeBnB platform has excellent infrastructure but is hampered by data scarcity.** The SARIMAX model is currently operating in fallback mode due to insufficient time-series data.

**Critical actions needed:**
1. 🔴 **IMMEDIATELY:** Backfill 6+ months of historical charging data
2. 🔴 **IMMEDIATELY:** Establish continuous data collection pipeline
3. 🟠 **THIS MONTH:** Expand and complete charger database (1000+ chargers)
4. 🟡 **ONGOING:** Add temporal/seasonal features and occupancy data

**Estimated Timeline:** 16 weeks to production-ready data, 8 weeks for meaningful improvements.

**Next Step:** Prioritize data sourcing from JOLT, bp pulse, and Victoria's transport authority.
