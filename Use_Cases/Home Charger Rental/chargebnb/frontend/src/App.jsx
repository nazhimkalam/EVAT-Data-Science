import { useEffect, useMemo, useRef, useState } from 'react';
import { createBooking, fetchListings, fetchPricing, fetchBookings } from './api.js';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

const defaultStart = new Date();
defaultStart.setMinutes(0, 0, 0);
const startIso = defaultStart.toISOString().slice(0, 16);

const defaultEnd = new Date(defaultStart.getTime() + 60 * 60 * 1000);
const endIso = defaultEnd.toISOString().slice(0, 16);

const defaultMapCenter = [-37.8136, 144.9631];

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
  console.warn('Failed to initialize map icon:', error);
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 2,
  }).format(value);
}

function App() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startTime, setStartTime] = useState(startIso);
  const [endTime, setEndTime] = useState(endIso);
  const [selectedListing, setSelectedListing] = useState(null);
  const [pricing, setPricing] = useState(null);
  const [bookingStatus, setBookingStatus] = useState(null);
  const [bookingError, setBookingError] = useState('');
  const [bookings, setBookings] = useState([]);
  const mapRef = useRef(null);
  const markerLayerRef = useRef(null);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingPayload, setBookingPayload] = useState({
    user_id: 1,
    vehicle: 'Tesla Model 3',
    promo: '',
  });

  useEffect(() => {
    console.log('Loading initial data...');
    loadListings().catch(error => console.error('Failed to load listings:', error));
    loadBookings().catch(error => console.error('Failed to load bookings:', error));
  }, []);

  useEffect(() => {
    console.log('Setting up map...');
    if (!mapRef.current) {
      try {
        const mapElement = document.getElementById('listings-map');
        if (!mapElement) {
          console.warn('Map container not found, retrying...');
          setTimeout(() => {
            const retryElement = document.getElementById('listings-map');
            if (retryElement) {
              initializeMap();
            }
          }, 100);
          return;
        }
        initializeMap();
      } catch (error) {
        console.error('Failed to initialize map:', error);
      }
    }

    updateMarkers();
  }, [listings]);

  const initializeMap = () => {
    try {
      console.log('Creating Leaflet map...');
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
      console.log('Map initialized successfully');
    } catch (error) {
      console.error('Failed to create map:', error);
    }
  };

  const updateMarkers = () => {
    if (!mapRef.current || !markerLayerRef.current) return;

    try {
      const markerLayer = markerLayerRef.current;
      markerLayer.clearLayers();

      const points = listings.filter((listing) => listing.lat && listing.lng);
      console.log(`Adding ${points.length} markers to map`);

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
          console.warn('Failed to add marker for listing:', listing.id, error);
        }
      });

      if (points.length > 0) {
        try {
          const bounds = markerLayer.getBounds();
          if (bounds.isValid()) {
            mapRef.current.fitBounds(bounds.pad(0.2), { maxZoom: 12 });
          }
        } catch (error) {
          console.warn('Failed to fit map bounds:', error);
        }
      }
    } catch (error) {
      console.error('Failed to update markers:', error);
    }
  };

  async function loadListings() {
    setLoading(true);
    try {
      console.log('Fetching listings...');
      const data = await fetchListings(startTime, endTime);
      console.log(`Loaded ${data.listings?.length || 0} listings`);
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
      console.log('Fetching bookings...');
      const data = await fetchBookings();
      console.log(`Loaded ${data.bookings?.length || 0} bookings`);
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
    const start = new Date(startTime);
    const end = new Date(endTime);
    const hours = Math.max(0, (end - start) / 3600000);
    return Math.round(hours * 100) / 100;
  }, [startTime, endTime]);

  const availabilitySummary = useMemo(() => {
    const total = listings.length;
    const available = listings.filter((item) => item.available).length;
    return `${available} / ${total} chargers available`;
  }, [listings]);

  async function handleCheckPricing(listing) {
    setSelectedListing(listing);
    setPricing(null);
    setBookingStatus(null);
    setBookingError('');

    if (!startTime) return;
    try {
      const data = await fetchPricing(listing.suburb, startTime);
      if (data) {
        setPricing(data);
        setBookingPayload((payload) => ({
          ...payload,
          listing_id: listing.id,
          suburb: listing.suburb,
          title: listing.title,
          quoted_price_per_hour: data.recommended_price,
        }));
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

    const payload = {
      ...bookingPayload,
      start: startTime,
      end: endTime,
      hours: selectedBookingHours,
      total_amount: parseFloat((pricing.recommended_price * selectedBookingHours).toFixed(2)),
    };

    try {
      const response = await createBooking(payload);
      setBookingStatus(response.booking || { success: true });
      setBookingError('');
      loadBookings();
    } catch (error) {
      setBookingError(error.message || 'Booking failed.');
      setBookingStatus(null);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero-section">
        <div className="hero-copy">
          <span className="eyebrow">ChargeBnB</span>
          <h1>Premium EV charging rental for modern hosts.</h1>
          <p>
            Discover charger listings with real-time AI pricing, flexible booking windows,
            and premium site performance.
          </p>
          <div className="hero-metrics">
            <div>
              <strong>{selectedBookingHours}h</strong>
              <span>booking window</span>
            </div>
            <div>
              <strong>{availabilitySummary}</strong>
              <span>availability</span>
            </div>
          </div>
        </div>
        <div className="hero-panel">
          <div className="hero-panel-title">Your search</div>
          <div className="hero-panel-field">
            <label>Start time</label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
            />
          </div>
          <div className="hero-panel-field">
            <label>End time</label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={(event) => setEndTime(event.target.value)}
            />
          </div>
          <button className="primary" onClick={loadListings} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh listings'}
          </button>
        </div>
      </header>

      <main className="layout">
        <section className="listings-panel">
          <div className="section-header">
            <div>
              <h2>Available chargers</h2>
              <p>Swipe through optimized charger listings and preview pricing instantly.</p>
            </div>
            <div className="status-pill">{availabilitySummary}</div>
          </div>

          <div className="listing-toolbar">
            <div className="filter-pill">
              {listings.length} charger{listings.length === 1 ? '' : 's'} loaded
            </div>
            <div className="muted">Refine time window and compare top listings without long page scrolling.</div>
          </div>

          <div className="listings-map-panel">
            <div className="map-header">
              <div>
                <h3>Charger map</h3>
                <p>Explore charger locations, availability, and pricing across Melbourne.</p>
              </div>
            </div>
            <div id="listings-map" className="listings-map" />
          </div>

          <div className="cards">
            {listings.length === 0 && !loading && (
              <div className="empty-state">No chargers available for this window.</div>
            )}
            {listings.map((listing) => (
              <article key={listing.id} className="card">
                <div className="card-head">
                  <div>
                    <h3>{listing.title}</h3>
                    <p>{listing.suburb}</p>
                  </div>
                  <span className="chip">Cluster {listing.cluster}</span>
                </div>
                <div className="card-meta">
                  <div>
                    <span>Price/hour</span>
                    <strong>{formatCurrency(listing.price_per_hour)}</strong>
                  </div>
                  <div>
                    <span>Connector</span>
                    <strong>{listing.connector}</strong>
                  </div>
                  <div>
                    <span>Rating</span>
                    <strong>{listing.kw} kW</strong>
                  </div>
                </div>
                <div className="card-footer">
                  <span className={`status-chip ${listing.available ? 'available' : 'unavailable'}`}>
                    {listing.available ? 'Available' : 'Unavailable'}
                  </span>
                  <button onClick={() => handleCheckPricing(listing)}>
                    View pricing
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="booking-panel">
          <div className="panel-header">
            <h2>Pricing & booking</h2>
            <p>Choose a charger, review the AI price recommendation, and confirm your booking.</p>
          </div>

          {!selectedListing && (
            <div className="empty-state">
              Select a listing to preview pricing and complete a booking.
            </div>
          )}

          {selectedListing && pricing && (
            <div className="booking-card">
              <div className="booking-card-header">
                <div>
                  <p className="eyebrow">Selected charger</p>
                  <h3>{selectedListing.title}</h3>
                  <p className="muted">{selectedListing.suburb}</p>
                </div>
                <div className="price-badge">{formatCurrency(pricing.recommended_price)} / hr</div>
              </div>

              <div className="pricing-grid">
                <div>
                  <span>Demand</span>
                  <strong>{pricing.expected_demand}</strong>
                </div>
                <div>
                  <span>Revenue</span>
                  <strong>{formatCurrency(pricing.expected_revenue)}</strong>
                </div>
                <div>
                  <span>Confidence</span>
                  <strong>{pricing.confidence_score}</strong>
                </div>
                <div>
                  <span>Price band</span>
                  <strong>{pricing.price_band}</strong>
                </div>
              </div>

              <form className="booking-form" onSubmit={handleSubmitBooking}>
                <div className="field-row">
                  <label>
                    <span>Vehicle</span>
                    <input
                      value={bookingPayload.vehicle}
                      onChange={(event) =>
                        setBookingPayload((prev) => ({
                          ...prev,
                          vehicle: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <label>
                    <span>Promo code</span>
                    <input
                      value={bookingPayload.promo}
                      onChange={(event) =>
                        setBookingPayload((prev) => ({
                          ...prev,
                          promo: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>

                <div className="booking-actions">
                  <button type="submit" className="primary">
                    Confirm booking
                  </button>
                </div>
              </form>

              {bookingStatus && (
                <div className="toast success">
                  Booking confirmed! ID: {bookingStatus.booking_id || 'pending'}
                </div>
              )}
              {bookingError && <div className="toast error">{bookingError}</div>}
            </div>
          )}
        </section>

        <section className="bookings-panel">
          <div className="section-header">
            <div>
              <h2>Recent bookings</h2>
              <p>Review the latest confirmed reservations for your ChargeBnB listings.</p>
            </div>
            <button className="secondary" onClick={loadBookings} disabled={bookingsLoading}>
              {bookingsLoading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>

          {bookings.length === 0 && !bookingsLoading ? (
            <div className="empty-state">No bookings have been created yet.</div>
          ) : (
            <div className="booking-list">
              {bookings.slice(0, 6).map((booking) => {
                const amount = Number(booking.frontend_total_amount ?? booking.backend_expected_total ?? 0);
                return (
                  <div key={booking.booking_id} className="booking-entry">
                    <div>
                      <span className="booking-label">{booking.title}</span>
                      <p>{booking.suburb}</p>
                    </div>
                    <div className="booking-meta">
                      <span>{new Date(booking.start).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                      <strong>{formatCurrency(amount)}</strong>
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