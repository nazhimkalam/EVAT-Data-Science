import { useEffect, useMemo, useRef, useState } from 'react';
import { createBooking, fetchListings, fetchPricing, fetchBookings } from './api.js';
import { SkeletonCardGrid, SkeletonBookingCard, SkeletonBookingList } from './Skeleton.jsx';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import { Box, TextField, Typography, Button, Stack, Paper, Card, CardContent, CardActions, Chip } from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

const defaultStartDayjs = dayjs().minute(0).second(0).millisecond(0);
const startIso = defaultStartDayjs.format('YYYY-MM-DDTHH:mm');

const defaultEndDayjs = defaultStartDayjs.add(1, 'hour');
const endIso = defaultEndDayjs.format('YYYY-MM-DDTHH:mm');

const defaultMapCenter = [-37.8136, 144.9631];

// EV vehicle types for dropdown
const EV_VEHICLES = [
  'Tesla Model 3',
  'Tesla Model Y',
  'Tesla Model S',
  'Nissan Leaf',
  'Chevrolet Bolt',
  'BMW i4',
  'BMW i3',
  'Audi Q4 e-tron',
  'Hyundai Ioniq 5',
  'Kia EV6',
  'Other',
];

// Promo code database (backend would validate this)
const VALID_PROMOS = {
  'WELCOME10': { discount: 0.10, description: '10% off' },
  'SUMMER20': { discount: 0.20, description: '20% off summer bookings' },
  'WEEKEND15': { discount: 0.15, description: '15% off weekends' },
};

let mapIcon;
try {
  mapIcon = L.icon({
    iconUrl,
    iconRetinaUrl,
    shadowUrl,
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    iconSize: [25, 41],
    shadowSize: [41, 41],
  });
  L.Marker.prototype.options.icon = mapIcon;
} catch (error) {
  // Silently fail - map will use default markers
}

function formatCurrency(value) {
  // Ensure value is a valid number
  const numValue = typeof value === 'string' ? parseFloat(value) : Number(value);

  // Return $0.00 for invalid values (NaN, null, undefined)
  if (isNaN(numValue)) {
    return '$0.00';
  }

  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 2,
  }).format(numValue);
}

function App() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startTime, setStartTime] = useState(defaultStartDayjs);
  const [endTime, setEndTime] = useState(defaultEndDayjs);
  const [selectedListing, setSelectedListing] = useState(null);
  const [pricing, setPricing] = useState(null);
  const [bookingStatus, setBookingStatus] = useState(null);
  const [bookingError, setBookingError] = useState('');
  const [bookings, setBookings] = useState([]);
  const mapRef = useRef(null);
  const markerLayerRef = useRef(null);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingPayload, setBookingPayload] = useState({
    user_id: undefined,
    vehicle: '',
    promo: '',
  });
  const [promoError, setPromoError] = useState('');
  const [promoDiscount, setPromoDiscount] = useState(0);
  const [isSubmittingBooking, setIsSubmittingBooking] = useState(false);

  const validatePromoCode = (code) => {
    if (!code) {
      setPromoError('');
      setPromoDiscount(0);
      return;
    }

    const upperCode = code.toUpperCase();
    const promoData = VALID_PROMOS[upperCode];

    if (promoData) {
      setPromoError('');
      setPromoDiscount(promoData.discount);
    } else {
      setPromoError('Invalid promo code');
      setPromoDiscount(0);
    }
  };

  const handlePromoChange = (event) => {
    const code = event.target.value;
    setBookingPayload((prev) => ({
      ...prev,
      promo: code,
    }));
    validatePromoCode(code);
  };

  useEffect(() => {
    loadListings().catch(error => console.error('Failed to load listings:', error));
    loadBookings().catch(error => console.error('Failed to load bookings:', error));
  }, []);

  useEffect(() => {
    if (!mapRef.current) {
      const mapElement = document.getElementById('listings-map');
      if (mapElement) {
        initializeMap();
      }
    }
    updateMarkers();
  }, [listings]);

  const initializeMap = () => {
    try {
      mapRef.current = L.map('listings-map', {
        center: defaultMapCenter,
        zoom: 10,
        scrollWheelZoom: false,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(mapRef.current);

      markerLayerRef.current = L.layerGroup().addTo(mapRef.current);
    } catch (error) {
      console.error('Failed to initialize map:', error);
    }
  };

  const updateMarkers = () => {
    if (!mapRef.current || !markerLayerRef.current) return;

    try {
      const markerLayer = markerLayerRef.current;
      markerLayer.clearLayers();

      const points = listings.filter((listing) => listing.lat && listing.lng);

      points.forEach((listing) => {
        try {
          const marker = L.marker([listing.lat, listing.lng]);
          marker.bindPopup(`
            <strong>${listing.title}</strong><br />
            ${listing.suburb}<br />
            ${formatCurrency(listing.price_per_hour)} / hr
          `);
          marker.addTo(markerLayer);
        } catch (error) {
          // Skip markers that fail to add
        }
      });

      if (points.length > 0) {
        try {
          const bounds = markerLayer.getBounds();
          if (bounds.isValid()) {
            mapRef.current.fitBounds(bounds.pad(0.2), { maxZoom: 12 });
          }
        } catch (error) {
          // Silently skip bounds fitting
        }
      }
    } catch (error) {
      console.error('Failed to update markers:', error);
    }
  };

  async function loadListings() {
    setLoading(true);
    try {
      const startIsoString = startTime.format('YYYY-MM-DDTHH:mm');
      const endIsoString = endTime.format('YYYY-MM-DDTHH:mm');
      const data = await fetchListings(startIsoString, endIsoString);
      await new Promise(resolve => setTimeout(resolve, 600));
      setListings(data.listings || []);
    } catch (error) {
      console.error('Error loading listings:', error);
      setListings([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadBookings() {
    setBookingsLoading(true);
    try {
      const data = await fetchBookings();
      await new Promise(resolve => setTimeout(resolve, 600));
      setBookings(data.bookings || []);
    } catch (error) {
      console.error('Error loading bookings:', error);
      setBookings([]);
    } finally {
      setBookingsLoading(false);
    }
  }

  const selectedBookingHours = useMemo(() => {
    if (!startTime || !endTime) return 0;
    const hours = Math.max(0, endTime.diff(startTime, 'hour', true));
    return Math.round(hours * 100) / 100;
  }, [startTime, endTime]);

  const bookingTotals = useMemo(() => {
    if (!pricing || !selectedBookingHours) {
      return {
        subtotal: 0,
        discount: 0,
        discountAmount: 0,
        total: 0,
      };
    }

    const hourlyRate = pricing.pricing?.recommended_price || 0;
    const subtotal = parseFloat((hourlyRate * selectedBookingHours).toFixed(2));
    const discountAmount = parseFloat((subtotal * promoDiscount).toFixed(2));
    const total = parseFloat((subtotal - discountAmount).toFixed(2));

    return {
      subtotal,
      discount: promoDiscount * 100,
      discountAmount,
      total,
    };
  }, [pricing, selectedBookingHours, promoDiscount]);

  const availabilitySummary = useMemo(() => {
    const total = listings.length;
    const available = listings.filter((item) => item.available).length;
    return `${available} / ${total} chargers available`;
  }, [listings]);

  const availableCount = useMemo(() => {
    return listings.filter((item) => item.available).length;
  }, [listings]);

  const handleStartTimeChange = (newStart) => {
    const now = dayjs();
    if (newStart.isBefore(now)) {
      alert('Cannot book in the past. Please select a future time.');
      return;
    }
    setStartTime(newStart);
    // Auto-adjust end time if it becomes invalid
    if (newStart.isSameOrAfter(endTime)) {
      setEndTime(newStart.add(1, 'hour'));
    }
  };

  const handleEndTimeChange = (newEnd) => {
    if (!newEnd) return;
    // Allow setting end time, validation happens on booking
    setEndTime(newEnd);
  };

  async function handleCheckPricing(listing) {
    setSelectedListing(listing);
    setPricing(null);
    setBookingStatus(null);
    setBookingError('');

    if (!startTime) return;
    try {
      const startIsoString = startTime.format('YYYY-MM-DDTHH:mm');
      const data = await fetchPricing(listing.suburb, startIsoString);
      await new Promise(resolve => setTimeout(resolve, 600));
      if (data && data.found) {
        // Restructure API response to match frontend expectations
        const structuredPricing = {
          found: data.found,
          suburb: data.suburb,
          cluster: data.cluster,
          pricing: {
            recommended_price: data.recommended_price,
            expected_revenue: data.expected_revenue,
            price_band: data.price_band,
          },
          demand: {
            expected_kw: data.expected_demand,
            confidence: data.confidence_score,
          },
          time_band: data.time_band,
        };
        setPricing(structuredPricing);
        setBookingPayload((payload) => ({
          ...payload,
          listing_id: listing.id,
          suburb: listing.suburb,
          title: listing.title,
          quoted_price_per_hour: data.recommended_price || 0,
        }));
      } else {
        setBookingError(data?.message || 'Pricing data not available');
      }
    } catch (error) {
      console.error('Error fetching pricing:', error);
      setBookingError('Failed to fetch pricing');
    }
  }

  async function handleSubmitBooking(event) {
    event.preventDefault();
    if (!pricing || !selectedListing) {
      setBookingError('Select a listing and pricing first.');
      return;
    }

    setIsSubmittingBooking(true);
    setBookingError('');

    const payload = {
      ...bookingPayload,
      start: startTime.format('YYYY-MM-DDTHH:mm'),
      end: endTime.format('YYYY-MM-DDTHH:mm'),
      hours: selectedBookingHours,
      total_amount: bookingTotals.total,
      discount_applied: promoDiscount > 0 ? bookingPayload.promo : null,
      discount_amount: bookingTotals.discountAmount,
    };

    try {
      console.log('Submitting booking payload:', payload);
      const response = await createBooking(payload);
      console.log('Full booking response:', JSON.stringify(response, null, 2));
      console.log('Response.success:', response.success);
      console.log('Response.booking:', response.booking);

      if (response.success && response.booking) {
        console.log('✓ Booking successful, displaying status');
        setBookingStatus(response.booking);
        setBookingError('');
        setIsSubmittingBooking(false);

        // Wait 3 seconds before resetting form to let user see confirmation
        setTimeout(() => {
          // Reset form after successful booking
          setBookingPayload({
            user_id: bookingPayload.user_id,
            vehicle: '',
            promo: '',
            listing_id: undefined,
            suburb: undefined,
            title: undefined,
            quoted_price_per_hour: 0,
          });
          setSelectedListing(null);
          setPricing(null);
          setBookingStatus(null);

          // Refresh both bookings and listings to show updated availability
          loadBookings();
          loadListings();
        }, 3000);
      } else {
        console.warn('Unexpected response structure:', { success: response.success, hasBooking: !!response.booking });
        // Even if response structure is odd, if we got here without an error, booking likely succeeded
        if (response.booking) {
          setBookingStatus(response.booking);
          setIsSubmittingBooking(false);
          setTimeout(() => {
            setBookingPayload({
              user_id: bookingPayload.user_id,
              vehicle: '',
              promo: '',
              listing_id: undefined,
              suburb: undefined,
              title: undefined,
              quoted_price_per_hour: 0,
            });
            setSelectedListing(null);
            setPricing(null);
            setBookingStatus(null);
            loadBookings();
            loadListings();
          }, 3000);
        } else if (response.booking_id) {
          setBookingStatus({ booking_id: response.booking_id, success: true });
          setIsSubmittingBooking(false);
          setTimeout(() => {
            setBookingPayload({
              user_id: bookingPayload.user_id,
              vehicle: '',
              promo: '',
              listing_id: undefined,
              suburb: undefined,
              title: undefined,
              quoted_price_per_hour: 0,
            });
            setSelectedListing(null);
            setPricing(null);
            setBookingStatus(null);
            loadBookings();
            loadListings();
          }, 3000);
        } else {
          setBookingError('Booking may have been created. Please refresh to confirm.');
          setIsSubmittingBooking(false);
        }
      }
    } catch (error) {
      console.error('Booking error:', error);
      setBookingError(error.message || 'Booking failed. Please try again.');
      setBookingStatus(null);
      setIsSubmittingBooking(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero-section">
        <div className="hero-copy">
          <span className="eyebrow">⚡ ChargeBnB</span>
          <h1>AI-Powered EV Charger Rental Platform</h1>
          <p>
            Discover premium electric vehicle chargers with intelligent pricing predictions,
            real-time availability tracking, and seamless booking experience.
          </p>
          <div className="hero-metrics">
            <div>
              <strong>{selectedBookingHours}</strong>
              <span>Hours Booking</span>
            </div>
            <div>
              <strong>{listings.length}</strong>
              <span>Chargers Available</span>
            </div>
          </div>
        </div>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <Paper
            elevation={0}
            sx={{
              p: 4,
              borderRadius: '1.5rem',
              background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
              border: '1px solid #e5e7eb',
              minWidth: '300px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
            }}
          >
            <Stack spacing={2.5}>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 700,
                  fontSize: '1.25rem',
                  lineHeight: 1.2,
                  color: '#1f2937',
                  fontFamily: "'Roboto', sans-serif"
                }}
              >
                Search for Chargers
              </Typography>

              <DateTimePicker
                label="Start time"
                value={startTime}
                onChange={handleStartTimeChange}
                ampm={false}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    size: 'small',
                    sx: {
                      '& .MuiOutlinedInput-root': {
                        borderRadius: '0.75rem',
                        cursor: 'pointer'
                      }
                    }
                  }
                }}
              />

              <DateTimePicker
                label="End time"
                value={endTime}
                onChange={handleEndTimeChange}
                ampm={false}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    size: 'small',
                    sx: {
                      '& .MuiOutlinedInput-root': {
                        borderRadius: '0.75rem',
                        cursor: 'pointer'
                      }
                    }
                  }
                }}
              />

              <Button
                fullWidth
                variant="contained"
                onClick={loadListings}
                disabled={loading}
                sx={{
                  background: 'linear-gradient(135deg, #FFC107 0%, #F57F17 100%)',
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  lineHeight: 1.2,
                  py: 1.25,
                  px: 2.5,
                  borderRadius: '0.75rem',
                  textTransform: 'none',
                  letterSpacing: '0.02em',
                  transition: 'all 0.2s ease-in-out',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                  border: 'none',
                  '&:hover:not(:disabled)': {
                    background: 'linear-gradient(135deg, #F57F17 0%, #E65100 100%)',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                    transform: 'translateY(-1px)',
                  },
                  '&:active:not(:disabled)': {
                    transform: 'translateY(0)',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  },
                  '&:disabled': {
                    opacity: 0.5,
                    boxShadow: 'none'
                  }
                }}
              >
                {loading ? '⏳ Searching...' : '🔍 Find Chargers'}
              </Button>
            </Stack>
          </Paper>
        </LocalizationProvider>
      </header>

      <main className="layout">
        <section className="listings-panel">
          <div className="section-header">
            <div>
              <h2>Available Chargers</h2>
              <p>Browse premium EV charging stations with real-time pricing and detailed specifications.</p>
            </div>
            <div className="status-pill" style={{ color: '#000000' }}>📍 {availabilitySummary}</div>
          </div>

          <div className="listing-toolbar">
            <div className="filter-pill" style={{ color: '#000000' }}>
              ✓ {availableCount} charger{availableCount === 1 ? '' : 's'} available
            </div>
            <div className="muted">Select a charger to view pricing, specifications, and booking details.</div>
          </div>

          <div className="listings-map-panel">
            <div className="map-header">
              <div>
                <h3>📍 Location Map</h3>
                <p>Interactive map showing charger locations, availability status, and pricing across Melbourne.</p>
              </div>
            </div>
            <div id="listings-map" className="listings-map" />
          </div>

          <div className="cards">
            {loading && <SkeletonCardGrid count={6} />}
            {listings.length === 0 && !loading && (
              <div className="empty-state">No chargers available for this window.</div>
            )}
            {!loading && listings.map((listing) => (
              <Card
                key={listing.id}
                sx={{
                  width: '100%',
                  minWidth: 320,
                  maxWidth: 480,
                  borderRadius: '1.25rem',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.06)',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  scrollSnapAlign: 'start',
                  display: 'flex',
                  flexDirection: 'column',
                  height: '100%',
                  border: 'none',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.06)'
                  }
                }}
              >
                <CardContent sx={{ p: 2.5, pb: 2, flex: 1 }}>
                  <Typography
                    variant="h6"
                    sx={{
                      fontWeight: 700,
                      mb: 0.3,
                      textTransform: 'capitalize',
                      fontSize: '1.125rem',
                      color: '#111827'
                    }}
                  >
                    {listing.title}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: '#64748b',
                      textTransform: 'capitalize',
                      mb: 2,
                      fontSize: '0.875rem'
                    }}
                  >
                    {listing.suburb}
                  </Typography>

                  <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.5 }}>
                    <Box>
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          color: '#78350f',
                          fontWeight: 600,
                          mb: 0.75,
                          textTransform: 'capitalize',
                          fontSize: '0.75rem',
                          letterSpacing: '0.3px'
                        }}
                      >
                        Price/hour
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color: '#451a03',
                          fontSize: '1rem'
                        }}
                      >
                        {formatCurrency(listing.price_per_hour)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          color: '#78350f',
                          fontWeight: 600,
                          mb: 0.75,
                          textTransform: 'capitalize',
                          fontSize: '0.75rem',
                          letterSpacing: '0.3px'
                        }}
                      >
                        Connector
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color: '#451a03',
                          textTransform: 'capitalize',
                          fontSize: '1rem'
                        }}
                      >
                        {listing.connector}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          color: '#78350f',
                          fontWeight: 600,
                          mb: 0.75,
                          textTransform: 'capitalize',
                          fontSize: '0.75rem',
                          letterSpacing: '0.3px'
                        }}
                      >
                        Power (kW)
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color: '#451a03',
                          fontSize: '1rem'
                        }}
                      >
                        {listing.kw} kW
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>

                <CardActions
                  sx={{
                    p: 2.5,
                    pt: 1.5,
                    display: 'flex',
                    gap: 1.5,
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <Chip
                    label={listing.available ? 'Available' : 'Unavailable'}
                    color={listing.available ? 'success' : 'error'}
                    variant="filled"
                    size="medium"
                    sx={{
                      fontWeight: 700,
                      borderRadius: '0.625rem',
                      height: '2.25rem',
                      fontSize: '0.875rem',
                      minWidth: '110px',
                      justifyContent: 'center'
                    }}
                  />
                  <Button
                    size="medium"
                    onClick={() => handleCheckPricing(listing)}
                    disabled={!listing.available}
                    variant="outlined"
                    sx={{
                      textTransform: 'capitalize',
                      fontWeight: 700,
                      borderRadius: '0.625rem',
                      px: 2,
                      py: 1.125,
                      height: '2.25rem',
                      border: '1px solid #D4A017',
                      color: '#1F2933',
                      backgroundColor: '#FFF8E1',
                      fontSize: '0.875rem',
                      flex: 1,
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        backgroundColor: '#F5D76E',
                        borderColor: '#B8860B',
                        color: '#111827',
                        boxShadow: '0 4px 8px rgba(0, 0, 0, 0.08)'
                      },
                      '&:active': {
                        backgroundColor: '#F0C847'
                      },
                      '&:disabled': {
                        opacity: 0.5,
                        borderColor: 'rgba(212, 160, 23, 0.5)',
                        color: 'rgba(31, 41, 51, 0.5)',
                        backgroundColor: 'rgba(255, 248, 225, 0.5)'
                      }
                    }}
                  >
                    View pricing
                  </Button>
                </CardActions>
              </Card>
            ))}
          </div>
        </section>

        <section className="booking-panel">
          <div className="panel-header">
            <h2>Booking & Payment</h2>
            <p>Review AI-optimized pricing, apply promo codes, and secure your booking instantly.</p>
          </div>

          {!selectedListing && (
            <div className="empty-state">
              💡 Select a charger from the list to view pricing details and complete your booking.
            </div>
          )}

          {selectedListing && !pricing && (
            <SkeletonBookingCard />
          )}

          {selectedListing && pricing && (
            <div className="booking-card">
              <div className="booking-card-header">
                <div>
                  <p className="eyebrow">⚡ Selected Charger</p>
                  <h3>{selectedListing.title}</h3>
                  <p className="muted">📍 {selectedListing.suburb}</p>
                </div>
                <div className="price-badge">{formatCurrency(pricing.pricing?.recommended_price)}/hr</div>
              </div>

              <div className="pricing-grid">
                <div>
                  <span>⚡ Expected Demand</span>
                  <strong>{pricing.demand?.expected_kw?.toFixed(0) || 0} kW</strong>
                </div>
                <div>
                  <span>💰 Revenue Estimate</span>
                  <strong>{formatCurrency(pricing.pricing?.expected_revenue || 0)}</strong>
                </div>
                <div>
                  <span>🎯 AI Confidence</span>
                  <strong>{((pricing.demand?.confidence || 0) * 100).toFixed(0)}%</strong>
                </div>
              </div>

              <div className={`price-mode-card price-mode-${pricing.pricing?.price_band || 'standard'}`}>
                <div className="price-mode-icon">
                  {pricing.pricing?.price_band === 'surge' ? '🔥' : pricing.pricing?.price_band === 'offpeak' ? '🌙' : '⚖️'}
                </div>
                <div className="price-mode-content">
                  <span className="price-mode-label">📊 Pricing Mode</span>
                  <h4 className="price-mode-name">
                    {pricing.pricing?.price_band === 'surge' ? '⬆️ Surge Pricing' : pricing.pricing?.price_band === 'offpeak' ? '⬇️ Off-Peak' : '⚖️ Standard'}
                  </h4>
                  <p className="price-mode-description">
                    {pricing.pricing?.price_band === 'surge'
                      ? 'High demand period • Premium rates active'
                      : pricing.pricing?.price_band === 'offpeak'
                      ? 'Low demand period • Discounted rates'
                      : 'Balanced demand • Regular pricing'}
                  </p>
                </div>
              </div>

              <form className="booking-form" onSubmit={handleSubmitBooking}>
                <div className="field-row">
                  <label>
                    <span>🚗 Vehicle Type</span>
                    <select
                      value={bookingPayload.vehicle}
                      onChange={(event) =>
                        setBookingPayload((prev) => ({
                          ...prev,
                          vehicle: event.target.value,
                        }))
                      }
                      required
                    >
                      <option value="">Select your electric vehicle</option>
                      {EV_VEHICLES.map((vehicle) => (
                        <option key={vehicle} value={vehicle}>
                          {vehicle}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>🎟️ Promo Code (Optional)</span>
                    <input
                      placeholder="e.g., WELCOME10"
                      value={bookingPayload.promo}
                      onChange={handlePromoChange}
                      maxLength={20}
                    />
                    {promoError && <span className="field-error">❌ {promoError}</span>}
                    {bookingPayload.promo && !promoError && VALID_PROMOS[bookingPayload.promo.toUpperCase()] && (
                      <span className="field-success">✓ {VALID_PROMOS[bookingPayload.promo.toUpperCase()].description}</span>
                    )}
                  </label>
                </div>

                {bookingTotals.subtotal > 0 && (
                  <div className="pricing-summary">
                    <div>
                      <span>Subtotal ({selectedBookingHours}h)</span>
                      <strong>{formatCurrency(bookingTotals.subtotal)}</strong>
                    </div>
                    {bookingTotals.discount > 0 && (
                      <div className="discount-row">
                        <span>Discount ({bookingTotals.discount}%)</span>
                        <strong>-{formatCurrency(bookingTotals.discountAmount)}</strong>
                      </div>
                    )}
                    <div className="total-row">
                      <span>Total</span>
                      <strong>{formatCurrency(bookingTotals.total)}</strong>
                    </div>
                  </div>
                )}

                <div className="booking-actions">
                  <button
                    type="submit"
                    className="primary"
                    disabled={!bookingPayload.vehicle || isSubmittingBooking}
                  >
                    {isSubmittingBooking ? '⏳ Processing...' : '✓ Confirm Booking'}
                  </button>
                </div>
              </form>

              {bookingStatus && (
                <div className="modal-overlay">
                  <div className="modal-content modal-success">
                    <div className="modal-success-icon">🎉</div>
                    <div className="modal-title">Booking Confirmed!</div>
                    <p className="modal-subtitle">
                      Your EV charger reservation has been successfully created and confirmed.
                    </p>
                    <div className="modal-details">
                      {bookingStatus.title && <div><span>⚡ Charger</span><strong>{bookingStatus.title}</strong></div>}
                      {bookingStatus.suburb && <div><span>📍 Location</span><strong>{bookingStatus.suburb}</strong></div>}
                      {bookingStatus.hours && <div><span>⏱️ Duration</span><strong>{bookingStatus.hours}h charging</strong></div>}
                      {bookingStatus.start && <div><span>📅 Starts</span><strong>{new Date(bookingStatus.start).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</strong></div>}
                      {bookingStatus.backend_expected_total !== undefined && <div><span>💳 Total Cost</span><strong>{formatCurrency(bookingStatus.backend_expected_total)}</strong></div>}
                    </div>
                    {bookingStatus.booking_id && (
                      <div className="modal-footer">
                        Reference: Booking #{bookingStatus.booking_id}
                      </div>
                    )}
                    <div className="modal-footer" style={{ marginTop: '1rem' }}>
                      ↻ Returning to listings in 3 seconds...
                    </div>
                  </div>
                </div>
              )}
              {bookingError && (
                <div className="toast error">
                  <strong>❌ Booking Error</strong>
                  <div style={{ marginTop: '0.35rem' }}>⚠️ {bookingError}</div>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="bookings-panel">
          <div className="section-header">
            <div>
              <h2>Recent Bookings</h2>
              <p>View all confirmed bookings and reservation details for your managed chargers.</p>
            </div>
            <button className="secondary icon-button" onClick={loadBookings} disabled={bookingsLoading} title="Refresh bookings list">
              <RefreshIcon sx={{ fontSize: '1.5rem', animation: bookingsLoading ? 'spin 1s linear infinite' : 'none' }} />
            </button>
          </div>

          {bookingsLoading && <SkeletonBookingList count={3} />}
          {!bookingsLoading && bookings.length === 0 && (
            <div className="empty-state">📭 No bookings yet. Your reservations will appear here.</div>
          )}
          {!bookingsLoading && bookings.length > 0 && (
            <div className="booking-list">
              {bookings.slice(0, 6).map((booking) => {
                const amount = Number(booking.backend_expected_total ?? booking.frontend_total_amount ?? 0);
                return (
                  <div key={booking.booking_id} className="booking-entry">
                    <div>
                      <span className="booking-label">⚡ {booking.title}</span>
                      <p>📍 {booking.suburb}</p>
                      <p className="booking-duration">⏱️ {booking.hours}h duration</p>
                    </div>
                    <div className="booking-meta">
                      <span>📅 {new Date(booking.start).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
                      <strong>💳 {formatCurrency(amount)}</strong>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;