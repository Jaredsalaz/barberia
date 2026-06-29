import { useState, useRef, useEffect } from 'react'
import type { CSSProperties, MouseEvent } from 'react'
import heroAsset from './assets/hero.svg'

type Message = {
  id: string
  role: 'user' | 'agent'
  text: string
}

type Tenant = {
  id: string
  name: string
  slug: string
  phone?: string
  address?: string
  latitude?: number
  longitude?: number
  is_featured: boolean
  image_url?: string
  description?: string
  business_hours?: any
  distance_km?: number
}

type TenantDetails = Tenant & {
  barbers?: { id: string; name: string; email: string }[]
  services?: { id: string; name: string; price: number; duration_minutes: number }[]
}

function App() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'agent', text: '¡Hola! Soy el asistente de reservas. Por favor, selecciona una barbería del directorio para iniciar el chat.' },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [landingTilt, setLandingTilt] = useState({ x: 0, y: 0 })
  const [scrollDepth, setScrollDepth] = useState(0)
  const [isScrolled, setIsScrolled] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Marketplace States
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [selectedTenantDetails, setSelectedTenantDetails] = useState<TenantDetails | null>(null)
  const [userLat, setUserLat] = useState<number>(16.7528) // Default Tuxtla Central
  const [userLon, setUserLon] = useState<number>(-93.1158)
  const [loadingTenants, setLoadingTenants] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Self-Service Registration States
  const [isRegistrationOpen, setIsRegistrationOpen] = useState(false)
  const [regStep, setRegStep] = useState(1)
  const [regEmail, setRegEmail] = useState('')
  const [regOtp, setRegOtp] = useState('')
  const [otpRequested, setOtpRequested] = useState(false)
  const [regShopName, setRegShopName] = useState('')
  const [regPhone, setRegPhone] = useState('')
  const [regAddress, setRegAddress] = useState('')
  const [regLatitude, setRegLatitude] = useState<number | undefined>(undefined)
  const [regLongitude, setRegLongitude] = useState<number | undefined>(undefined)
  const [regDescription, setRegDescription] = useState('')
  const [regImageUrl, setRegImageUrl] = useState('')
  const [regOwnerName, setRegOwnerName] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regPlan, setRegPlan] = useState<'normal' | 'pro'>('normal')
  const [regLoading, setRegLoading] = useState(false)
  const [regError, setRegError] = useState('')

  const mapRef = useRef<any>(null)
  const markersGroupRef = useRef<any>(null)
  
  const miniMapRef = useRef<any>(null)
  const miniMarkerRef = useRef<any>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Get active API base URL
  const getApiBase = () => {
    return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8001'
      : 'https://balam-barberia-api.fly.dev';
  }

  // Fetch tenants sorted by distance
  const fetchTenants = async (lat?: number, lon?: number) => {
    setLoadingTenants(true)
    const apiBase = getApiBase()
    const currentLat = lat ?? userLat
    const currentLon = lon ?? userLon
    
    let url = `${apiBase}/api/v1/tenants/?lat=${currentLat}&lon=${currentLon}`
    
    try {
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setTenants(data)
      }
    } catch (error) {
      console.error("[Marketplace] Error fetching tenants:", error)
    } finally {
      setLoadingTenants(false)
    }
  }

  // Request browser geolocation on load
  const requestLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude
          const lon = position.coords.longitude
          setUserLat(lat)
          setUserLon(lon)
          fetchTenants(lat, lon)
        },
        (error) => {
          console.warn("[Geolocation] Permission denied or failed, using defaults:", error.message)
          fetchTenants(userLat, userLon)
        }
      )
    } else {
      fetchTenants(userLat, userLon)
    }
  }

  // Initial load
  useEffect(() => {
    requestLocation()
    
    const handleScroll = () => {
      setScrollDepth(window.scrollY * 0.2)
      setIsScrolled(window.scrollY > 50)

      const reveals = document.querySelectorAll('.reveal')
      reveals.forEach((reveal) => {
        const windowHeight = window.innerHeight
        const revealTop = reveal.getBoundingClientRect().top
        const revealPoint = 150
        if (revealTop < windowHeight - revealPoint) {
          reveal.classList.add('active')
        }
      })
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Self-Service Registration Handlers
  const handleRequestOtp = async () => {
    if (!regEmail.trim()) {
      setRegError('Por favor ingresa un correo electrónico válido.')
      return
    }
    setRegLoading(true)
    setRegError('')
    try {
      const apiBase = getApiBase()
      const response = await fetch(`${apiBase}/api/v1/registration/request-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: regEmail })
      })
      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Error al enviar el código de verificación.')
      }
      setOtpRequested(true)
    } catch (err: any) {
      setRegError(err.message || 'Error de conexión.')
    } finally {
      setRegLoading(false)
    }
  }

  const handleVerifyOtp = async () => {
    if (!regOtp.trim()) {
      setRegError('Por favor ingresa el código OTP.')
      return
    }
    setRegLoading(true)
    setRegError('')
    try {
      const apiBase = getApiBase()
      const response = await fetch(`${apiBase}/api/v1/registration/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: regEmail, otp: regOtp })
      })
      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'El código es incorrecto o ha expirado.')
      }
      setRegStep(2) // Move to shop details
    } catch (err: any) {
      setRegError(err.message || 'Error de conexión.')
    } finally {
      setRegLoading(false)
    }
  }

  const handleLocateRegistration = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude
          const lon = position.coords.longitude
          setRegLatitude(lat)
          setRegLongitude(lon)

          // Center mini-map and update marker
          const L = (window as any).L
          if (L && miniMapRef.current) {
            miniMapRef.current.setView([lat, lon], 15)
            if (miniMarkerRef.current) {
              miniMarkerRef.current.setLatLng([lat, lon])
            } else {
              miniMarkerRef.current = L.marker([lat, lon]).addTo(miniMapRef.current)
            }
          }
        },
        (error) => {
          console.warn("[Geolocation] Could not detect location for registration:", error.message)
          const lat = userLat
          const lon = userLon
          setRegLatitude(lat)
          setRegLongitude(lon)

          const L = (window as any).L
          if (L && miniMapRef.current) {
            miniMapRef.current.setView([lat, lon], 15)
            if (miniMarkerRef.current) {
              miniMarkerRef.current.setLatLng([lat, lon])
            } else {
              miniMarkerRef.current = L.marker([lat, lon]).addTo(miniMapRef.current)
            }
          }
        }
      )
    } else {
      const lat = userLat
      const lon = userLon
      setRegLatitude(lat)
      setRegLongitude(lon)

      const L = (window as any).L
      if (L && miniMapRef.current) {
        miniMapRef.current.setView([lat, lon], 15)
        if (miniMarkerRef.current) {
          miniMarkerRef.current.setLatLng([lat, lon])
        } else {
          miniMarkerRef.current = L.marker([lat, lon]).addTo(miniMapRef.current)
        }
      }
    }
  }

  const renderPayPalButtons = () => {
    const container = document.getElementById('paypal-button-container');
    if (!container) {
      console.warn("PayPal container element not found yet");
      return;
    }
    container.innerHTML = ''; // prevent duplicates
    
    if ((window as any).paypal) {
      (window as any).paypal.Buttons({
        createOrder: async () => {
          setRegError('');
          try {
            const apiBase = getApiBase();
            const response = await fetch(`${apiBase}/api/v1/registration/create-paypal-order`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                plan: regPlan,
                email: regEmail
              })
            });
            if (!response.ok) {
              const errData = await response.json();
              throw new Error(errData.detail || 'Error al generar la orden en PayPal.');
            }
            const data = await response.json();
            return data.order_id;
          } catch (err: any) {
            setRegError(err.message || 'Error al conectar con el servidor.');
            console.error(err);
          }
        },
        onApprove: async (data: any) => {
          setRegLoading(true);
          setRegError('');
          try {
            const apiBase = getApiBase();
            const response = await fetch(`${apiBase}/api/v1/registration/complete`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                order_id: data.orderID,
                plan: regPlan,
                email: regEmail,
                shop_name: regShopName,
                phone: regPhone,
                address: regAddress,
                latitude: regLatitude || userLat,
                longitude: regLongitude || userLon,
                description: regDescription,
                image_url: regImageUrl,
                owner_name: regOwnerName,
                password: regPassword
              })
            });
            
            if (!response.ok) {
              const errData = await response.json();
              throw new Error(errData.detail || 'El cobro se realizó pero la barbería no pudo ser guardada.');
            }
            
            const result = await response.json();
            console.log("[Registration] Completed:", result);
            setRegStep(5);
            fetchTenants(); // reload directory list
          } catch (err: any) {
            setRegError(err.message || 'Ocurrió un error al registrar tu barbería.');
            console.error(err);
          } finally {
            setRegLoading(false);
          }
        },
        onError: (err: any) => {
          setRegError('El pago fue cancelado o no pudo ser procesado.');
          console.error(err);
        }
      }).render('#paypal-button-container');
    } else {
      setRegError('El SDK de PayPal no se ha cargado correctamente.');
    }
  };

  const resetRegistrationState = () => {
    setIsRegistrationOpen(false)
    setRegStep(1)
    setRegEmail('')
    setRegOtp('')
    setOtpRequested(false)
    setRegShopName('')
    setRegPhone('')
    setRegAddress('')
    setRegLatitude(undefined)
    setRegLongitude(undefined)
    setRegDescription('')
    setRegImageUrl('')
    setRegOwnerName('')
    setRegPassword('')
    setRegPlan('normal')
    setRegLoading(false)
    setRegError('')
  }

  useEffect(() => {
    if (isRegistrationOpen && regStep === 4) {
      const loadPaypal = async () => {
        const existingScript = document.getElementById('paypal-sdk-script');
        if (!existingScript) {
          const script = document.createElement('script');
          script.id = 'paypal-sdk-script';
          script.src = `https://www.paypal.com/sdk/js?client-id=AdUiyksRFA1aEH6xME-RIkiHyk03PpbFDM4kvuHAOrjf_3U62Qywy6fizIfqp0aktUkTiVmZM-VPcmYV&currency=MXN`;
          script.async = true;
          script.onload = () => {
            renderPayPalButtons();
          };
          script.onerror = () => {
            setRegError('Error al cargar la plataforma de pagos de PayPal.');
          };
          document.body.appendChild(script);
        } else {
          setTimeout(() => {
            renderPayPalButtons();
          }, 100);
        }
      };
      loadPaypal();
    }
  }, [isRegistrationOpen, regStep, regPlan]);

  // Initialize and handle Leaflet Mini Map inside the Registration Wizard
  useEffect(() => {
    const L = (window as any).L;
    if (!L) return;

    if (isRegistrationOpen && regStep === 2) {
      // Small timeout to ensure the DOM element #mini-map-container is mounted and visible
      const timer = setTimeout(() => {
        const container = document.getElementById('mini-map-container');
        if (!container) return;

        const defaultLat = regLatitude || userLat;
        const defaultLon = regLongitude || userLon;

        // Initialize map if it doesn't exist
        if (!miniMapRef.current) {
          miniMapRef.current = L.map('mini-map-container').setView([defaultLat, defaultLon], 14);

          // Dark Matter tiles for cohesive theme
          L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; CARTO',
            maxZoom: 20
          }).addTo(miniMapRef.current);

          // Add click listener to pick coordinates
          miniMapRef.current.on('click', (e: any) => {
            const { lat, lng } = e.latlng;
            setRegLatitude(lat);
            setRegLongitude(lng);

            if (miniMarkerRef.current) {
              miniMarkerRef.current.setLatLng([lat, lng]);
            } else {
              miniMarkerRef.current = L.marker([lat, lng]).addTo(miniMapRef.current);
            }
          });
        } else {
          miniMapRef.current.setView([defaultLat, defaultLon], 14);
        }

        // Set initial marker if coordinates are present
        if (regLatitude && regLongitude) {
          if (miniMarkerRef.current) {
            miniMarkerRef.current.setLatLng([regLatitude, regLongitude]);
          } else {
            miniMarkerRef.current = L.marker([regLatitude, regLongitude]).addTo(miniMapRef.current);
          }
        }
      }, 100);

      return () => {
        clearTimeout(timer);
        if (miniMapRef.current) {
          miniMapRef.current.remove();
          miniMapRef.current = null;
          miniMarkerRef.current = null;
        }
      };
    }
  }, [isRegistrationOpen, regStep]);

  // Initialize Leaflet Map
  useEffect(() => {
    const L = (window as any).L;
    if (!L) return;

    if (!mapRef.current) {
      // Map instance
      mapRef.current = L.map('map-container').setView([userLat, userLon], 13)
      
      // CartoDB Dark Matter tile layer
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
      }).addTo(mapRef.current)

      markersGroupRef.current = L.layerGroup().addTo(mapRef.current)
    } else {
      mapRef.current.setView([userLat, userLon], 13)
    }
  }, [userLat, userLon, tenants])

  // Update map markers when tenants load
  useEffect(() => {
    const L = (window as any).L;
    if (!L || !mapRef.current || !markersGroupRef.current) return;

    markersGroupRef.current.clearLayers()

    // Add user marker
    const userIcon = L.divIcon({
      html: '<div style="background-color: #3b82f6; width: 14px; height: 14px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(59,130,246,0.8);"></div>',
      className: 'user-marker-icon',
      iconSize: [14, 14]
    })
    L.marker([userLat, userLon], { icon: userIcon }).addTo(markersGroupRef.current).bindPopup("Tú estás aquí")

    // Add tenant markers
    tenants.forEach((t) => {
      if (t.latitude && t.longitude) {
        const markerColor = t.is_featured ? '#7c3aed' : '#ec4899';
        const markerIcon = L.divIcon({
          html: `<div style="background-color: ${markerColor}; width: 18px; height: 18px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 12px ${markerColor};"></div>`,
          className: 'tenant-marker-icon',
          iconSize: [18, 18]
        })

        const popupContent = `
          <div style="color: #0f172a; font-family: sans-serif; min-width: 160px; padding: 4px;">
            <strong style="display:block;font-size:14px;margin-bottom:3px;color:#1e1b4b;">${t.name}</strong>
            <span style="font-size:11px;color:#475569;display:block;margin-bottom:6px;">${t.address || ''}</span>
            <button id="map-btn-${t.id}" style="background: linear-gradient(120deg, #7c3aed, #2563eb); color: white; border: none; padding: 6px 12px; border-radius: 12px; font-size: 11px; font-weight:600; cursor: pointer; width: 100%; box-shadow: 0 2px 5px rgba(124,58,237,0.3);">Agendar con AI</button>
          </div>
        `

        const marker = L.marker([t.latitude, t.longitude], { icon: markerIcon })
          .addTo(markersGroupRef.current)
          .bindPopup(popupContent)

        marker.on('popupopen', () => {
          const btn = document.getElementById(`map-btn-${t.id}`)
          if (btn) {
            btn.onclick = () => {
              handleSelectTenant(t)
            }
          }
        })
      }
    })
  }, [tenants, userLat, userLon])

  const calculateTilt = (event: MouseEvent<HTMLElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect()
    const x = (event.clientX - bounds.left - bounds.width / 2) / 30
    const y = (event.clientY - bounds.top - bounds.height / 2) / 30
    return { x, y: -y }
  }

  const handleLandingMove = (event: MouseEvent<HTMLElement>) => {
    setLandingTilt(calculateTilt(event))
  }

  const resetLandingMove = () => {
    setLandingTilt({ x: 0, y: 0 })
  }

  // Handle select tenant for chat widget
  const handleSelectTenant = async (tenant: Tenant) => {
    setSelectedTenant(tenant)
    setIsOpen(true)
    setMessages([
      { id: '1', role: 'agent', text: `¡Hola! Soy el asistente virtual de ${tenant.name}. ¿En qué te puedo ayudar hoy?` }
    ])
    setSelectedTenantDetails(null)

    // Load full tenant details (services and barbers)
    const apiBase = getApiBase()
    try {
      const response = await fetch(`${apiBase}/api/v1/tenants/${tenant.slug}`)
      if (response.ok) {
        const details = await response.json()
        setSelectedTenantDetails(details)
      }
    } catch (err) {
      console.error("[Details] Error fetching tenant details:", err)
    }
  }

  // Send message to AI assistant
  const handleSend = async () => {
    if (!input.trim() || !selectedTenant) return

    const userMessage: Message = { id: Date.now().toString(), role: 'user', text: input }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    const apiBase = getApiBase()

    try {
      const response = await fetch(`${apiBase}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.text,
          shop_id: selectedTenant.id,
          shop_name: selectedTenant.name,
        }),
      })

      const data = await response.json()

      const agentMessage: Message = {
        id: Date.now().toString() + 'a',
        role: 'agent',
        text: data.response || 'Hubo un error al procesar tu solicitud.',
      }
      setMessages((prev) => [...prev, agentMessage])
    } catch (error) {
      console.error(error)
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: 'agent', text: 'Lo siento, hay problemas de conexión con el asistente.' },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // Filtered tenants for search bar
  const filteredTenants = tenants.filter(t => 
    t.name.toLowerCase().includes(searchText.toLowerCase()) || 
    (t.address && t.address.toLowerCase().includes(searchText.toLowerCase()))
  )

  const featuredTenants = tenants.filter(t => t.is_featured)

  const landingHeroStyle = {
    '--landing-tilt-x': `${landingTilt.x}px`,
    '--landing-tilt-y': `${landingTilt.y}px`,
    '--landing-scroll': `${scrollDepth}px`,
  } as CSSProperties

  return (
    <>
      <nav className={`balam-navbar ${isScrolled ? 'scrolled' : ''} ${isMobileMenuOpen ? 'mobile-menu-open' : ''}`}>
        <a href="#" className="balam-logo" onClick={() => setIsMobileMenuOpen(false)}>
          Balam <span>Platform</span>
        </a>
        <button 
          className="balam-hamburger" 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Menú de navegación"
        >
          <span className="bar"></span>
          <span className="bar"></span>
          <span className="bar"></span>
        </button>
        <div className={`balam-nav-links ${isMobileMenuOpen ? 'show' : ''}`}>
          <a href="#map-section" onClick={() => setIsMobileMenuOpen(false)}>Mapa local</a>
          <a href="#featured-section" onClick={() => setIsMobileMenuOpen(false)}>Destacadas</a>
          <a href="#directory-section" onClick={() => setIsMobileMenuOpen(false)}>Directorio</a>
          <a href="#" className="register-shop-link" onClick={(e) => { e.preventDefault(); setIsRegistrationOpen(true); setIsMobileMenuOpen(false); }}>
            Registra tu barbería
          </a>
          {selectedTenant ? (
            <button className="nav-cta balam-primary-btn" style={{ marginTop: 0 }} onClick={() => { setIsOpen(true); setIsMobileMenuOpen(false); }}>
              Hablar con {selectedTenant.name}
            </button>
          ) : (
            <button className="nav-cta balam-primary-btn" style={{ marginTop: 0 }} onClick={() => {
              document.getElementById('directory-section')?.scrollIntoView({ behavior: 'smooth' });
              setIsMobileMenuOpen(false);
            }}>
              Seleccionar Barbería
            </button>
          )}
        </div>
      </nav>

      <main className="balam-page">
        <section
          className="balam-landing-hero"
          style={landingHeroStyle}
          onMouseMove={handleLandingMove}
          onMouseLeave={resetLandingMove}
        >
          <img
            className="balam-landing-video"
            src="https://imgs.search.brave.com/Bd_3aVSy_pdph6nhn6dB1_sHovb2hwWJzsTFjEKDhKE/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9zdGF0/aWMud2l4c3RhdGlj/LmNvbS9tZWRpYS9m/ZjViMTNfMmQ1YTQ5/NmJiZDQ1NDQ4NTlh/MzZhY2QwNGMwYTcw/MTh-bXYyLmpwZy92/MS9maWxsL3dfMTcz/MSxoXzY5OSxhbF9j/LHFfODUsdXNtXzAu/NjZfMS4wMF8wLjAx/LGVuY19hdmlmLHF1/YWxpdHlfYXV0by9i/YXJiZXJpYSUyNTI1/MjUyNTIwcGlydWxp/JTI1MjUyNTI1MjBm/aW5hLmpwZw"
            alt="Balam Platform Banner"
            style={{ objectPosition: 'center 30%' }}
          />
          <div className="balam-landing-overlay" />
          <div className="balam-landing-content">
            <p className="balam-chip">Balam SaaS • Barbería Marketplace</p>
            <h1>
              Encuentra y agenda en <span>barberías premium</span> de tu zona
            </h1>
            <p>
              Explora horarios disponibles, cotiza servicios y reserva al instante chateando con asistentes de Inteligencia Artificial dedicados.
            </p>
            
            <div className="balam-search-bar">
              <input 
                type="text" 
                placeholder="Buscar por nombre, zona o dirección..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <button type="button" onClick={requestLocation}>Compartir ubicación</button>
            </div>
          </div>
          <div className="balam-landing-3d">
            <img 
              src={heroAsset} 
              alt="Balam Scissors decoration" 
              aria-hidden="true" 
              style={{ width: '100%', height: '100%', filter: 'drop-shadow(0 0 20px rgba(124, 58, 237, 0.6))' }}
            />
          </div>
        </section>

        {/* Interactive Map Section */}
        <section id="map-section" className="map-container-wrapper reveal">
          <div className="balam-section-title">
            <p>Geolocalización en Tiempo Real</p>
            <h2>Explora barberías cercanas en el mapa</h2>
          </div>
          <div 
            id="map-container" 
            style={{ 
              height: '420px', 
              borderRadius: '24px', 
              border: '1px solid rgba(148, 163, 184, 0.25)', 
              marginTop: '18px',
              boxShadow: 'var(--balam-shadow)',
              zIndex: 10
            }}
          />
        </section>

        {/* Featured / Sponsored Ads Section */}
        {featuredTenants.length > 0 && (
          <section id="featured-section" className="balam-team-section reveal">
            <div className="balam-section-title">
              <p>Socios Destacados</p>
              <h2>Estudios Premium recomendados en tu zona</h2>
            </div>
            <div className="balam-team-grid">
              {featuredTenants.map((tenant) => (
                <article key={tenant.id} className="balam-team-card" style={{ cursor: 'pointer' }} onClick={() => handleSelectTenant(tenant)}>
                  <img src={tenant.image_url || 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=600&q=80'} alt={tenant.name} loading="lazy" />
                  <div className="balam-team-card-content">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="marketplace-badge">Patrocinado ⭐</span>
                      {tenant.distance_km !== null && (
                        <span className="distance-badge">{tenant.distance_km} km</span>
                      )}
                    </div>
                    <h3 style={{ marginTop: '8px' }}>{tenant.name}</h3>
                    <p style={{ minHeight: '60px' }}>{tenant.description || 'Barbería registrada con estilistas premium.'}</p>
                    <span style={{ fontSize: '12px', color: '#60a5fa', display: 'block', marginTop: '10px' }}>📍 {tenant.address || 'Ubicación Premium'}</span>
                    <button className="balam-primary-btn" style={{ width: '100%', marginTop: '12px' }} onClick={(e) => {
                      e.stopPropagation();
                      handleSelectTenant(tenant);
                    }}>Agendar cita con AI</button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        <section className="balam-parallax-section reveal">
          <div>
            <p>Plataforma Inteligente</p>
            <h2>Elige los horarios que mejor te parezcan, sin esperas en teléfono</h2>
          </div>
        </section>

        {/* General Directory List */}
        <section id="directory-section" className="balam-services-section reveal">
          <div className="balam-section-title">
            <p>Directorio General</p>
            <h2>Todas las barberías dadas de alta en la plataforma</h2>
          </div>
          {loadingTenants ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--balam-text-soft)' }}>
              Cargando catálogo de barberías locales...
            </div>
          ) : filteredTenants.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--balam-text-soft)' }}>
              No se encontraron barberías que coincidan con la búsqueda.
            </div>
          ) : (
            <div className="balam-services-grid">
              {filteredTenants.map((tenant) => (
                <article key={tenant.id} className="balam-service-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <img src={tenant.image_url || 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=600&q=80'} alt={tenant.name} loading="lazy" />
                  <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', color: 'var(--balam-text-soft)', textTransform: 'uppercase', fontWeight: 600 }}>{tenant.is_featured ? '⭐ Destacada' : 'Normal'}</span>
                      {tenant.distance_km !== null && (
                        <span className="distance-badge">{tenant.distance_km} km</span>
                      )}
                    </div>
                    <h3 style={{ marginTop: '8px', color: 'white', fontSize: '18px' }}>{tenant.name}</h3>
                    <p style={{ flexGrow: 1, minHeight: '60px', marginTop: '6px' }}>{tenant.description || 'Estilistas expertos con horarios flexibles y atención pro.'}</p>
                    <span style={{ fontSize: '12px', color: '#c4d1ee', display: 'block', marginTop: '10px' }}>📍 {tenant.address || 'Ubicación registrada'}</span>
                    <button className="balam-primary-btn" style={{ width: '100%', marginTop: '16px' }} onClick={() => handleSelectTenant(tenant)}>
                      Chatear y Agendar
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <footer className="balam-footer">
          <div className="balam-footer-grid">
            <div className="balam-footer-info">
              <a href="#" className="balam-logo">
                Balam <span>Platform</span>
              </a>
              <p>Unificando a las mejores barberías en una sola plataforma inteligente para agendar de forma instantánea.</p>
              <div className="balam-socials">
                <a href="#" className="balam-social-btn">IG</a>
                <a href="#" className="balam-social-btn">FB</a>
                <a href="#" className="balam-social-btn">TW</a>
              </div>
            </div>
            <div className="balam-footer-col">
              <h4>Navegación</h4>
              <ul>
                <li><a href="#map-section">Mapa</a></li>
                <li><a href="#featured-section">Destacadas</a></li>
                <li><a href="#directory-section">Directorio</a></li>
              </ul>
            </div>
            <div className="balam-footer-col">
              <h4>Soporte</h4>
              <ul>
                <li>Centro de ayuda</li>
                <li style={{ cursor: 'pointer' }} onClick={() => setIsRegistrationOpen(true)}>Registro de barberías</li>
                <li>Términos y condiciones</li>
              </ul>
            </div>
            <div className="balam-footer-col">
              <h4>¿Eres barbero?</h4>
              <ul>
                <li style={{ cursor: 'pointer' }} onClick={() => setIsRegistrationOpen(true)}>Registrar mi barbería</li>
                <li>Descargar App</li>
                <li>Precios SaaS</li>
              </ul>
            </div>
          </div>
          <div className="balam-footer-bottom">
            <p>&copy; 2026 Balam Platform SaaS. Todos los derechos reservados.</p>
            <p>Diseño por Antigravity AI</p>
          </div>
        </footer>
      </main>

      {/* Floating Chatbot Widget */}
      <div className="balam-widget-container">
        {selectedTenant && !isOpen && (
          <button className="balam-agent-spotlight" type="button" onClick={() => setIsOpen(true)}>
            <span>Agendando en:</span>
            <strong>{selectedTenant.name}</strong>
          </button>
        )}
        {isOpen && (
          <div className="balam-chat-window">
            <div className="balam-chat-header">
              <div>
                <h3>{selectedTenant ? selectedTenant.name : 'Balam Assistant'}</h3>
                <p>{selectedTenant ? (selectedTenant.address ? selectedTenant.address : 'Chat Inteligente') : 'Selecciona una barbería para chatear'}</p>
              </div>
              <button
                className="balam-close-btn"
                onClick={() => setIsOpen(false)}
                aria-label="Cerrar asistente"
              >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <section className="balam-chat-intro">
              <p>Asistente de Reservas Virtual</p>
              <h4>{selectedTenant ? `Agenda en ${selectedTenant.name} de forma instantánea:` : 'Selecciona una barbería del directorio para iniciar:'}</h4>
              
              {selectedTenant ? (
                <>
                  <p style={{ marginTop: '8px', textTransform: 'none', color: '#1e293b', fontSize: '12px' }}>{selectedTenant.description}</p>
                  
                  {selectedTenantDetails && selectedTenantDetails.services && (
                    <div className="chat-details-services">
                      <strong>Nuestros Servicios:</strong>
                      {selectedTenantDetails.services.map(s => (
                        <span key={s.id} className="chat-service-tag">{s.name} (${s.price})</span>
                      ))}
                    </div>
                  )}

                  <div className="balam-quick-actions">
                    <button type="button" onClick={() => setInput('¿Qué horarios tienen hoy?')}>
                      Horarios de hoy
                    </button>
                    <button type="button" onClick={() => setInput('Quiero agendar una cita')}>
                      Agendar cita
                    </button>
                    <button type="button" onClick={() => setInput('¿Qué servicios ofrecen?')}>
                      Ver servicios
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ marginTop: '10px', fontSize: '12px', color: '#475569' }}>
                  Elige cualquiera de nuestras barberías asociadas en el directorio y podrás agendar tu cita chateando con el bot asignado.
                </div>
              )}
            </section>

            <div className="balam-chat-messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`balam-message ${msg.role}`}>
                  {msg.text}
                </div>
              ))}
              {isLoading && (
                <div className="balam-message agent">
                  <div className="balam-typing">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="balam-chat-input-area">
              <input
                type="text"
                placeholder={selectedTenant ? "Escribe tu mensaje para reservar..." : "Selecciona una barbería primero"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                disabled={isLoading || !selectedTenant}
              />
              <button onClick={handleSend} disabled={isLoading || !input.trim() || !selectedTenant}>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
          </div>
        )}

        {selectedTenant && (
          <button className="balam-trigger-btn" onClick={() => setIsOpen(!isOpen)}>
            {isOpen ? (
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            ) : (
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            )}
          </button>
        )}
      </div>

      {isRegistrationOpen && (
        <div className="balam-modal-overlay">
          <div className="balam-wizard-modal">
            <button className="balam-wizard-close" onClick={resetRegistrationState}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>

            <div style={{ textAlign: 'center', marginBottom: '10px' }}>
              <h2 style={{ fontFamily: 'Manrope', color: 'white', fontSize: '24px' }}>Registra tu Barbería</h2>
              <p style={{ color: 'var(--balam-text-soft)', fontSize: '14px', marginTop: '4px' }}>Únete a la plataforma Balam y destaca tu negocio</p>
            </div>

            {/* progress bar */}
            <div className="balam-wizard-progress">
              <div 
                className="balam-wizard-progress-bar" 
                style={{ width: `${((regStep - 1) / 4) * 100}%` }}
              />
              <div className={`balam-progress-step ${regStep >= 1 ? 'active' : ''} ${regStep > 1 ? 'completed' : ''}`}>1</div>
              <div className={`balam-progress-step ${regStep >= 2 ? 'active' : ''} ${regStep > 2 ? 'completed' : ''}`}>2</div>
              <div className={`balam-progress-step ${regStep >= 3 ? 'active' : ''} ${regStep > 3 ? 'completed' : ''}`}>3</div>
              <div className={`balam-progress-step ${regStep >= 4 ? 'active' : ''} ${regStep > 4 ? 'completed' : ''}`}>4</div>
              <div className={`balam-progress-step ${regStep >= 5 ? 'active' : ''}`}>5</div>
            </div>

            <div className="balam-wizard-body">
              {regError && (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  padding: '12px',
                  borderRadius: '12px',
                  fontSize: '13px',
                  marginBottom: '16px',
                  textAlign: 'left'
                }}>
                  ⚠️ {regError}
                </div>
              )}

              {/* STEP 1: OTP Verification */}
              {regStep === 1 && (
                <div>
                  <h3 style={{ color: 'white', fontSize: '18px', marginBottom: '12px' }}>Paso 1: Verifica tu correo electrónico</h3>
                  <p style={{ color: 'var(--balam-text-soft)', fontSize: '14px', marginBottom: '20px', lineHeight: '1.5', textAlign: 'left' }}>
                    Para comenzar el registro, ingresa tu correo electrónico. Te enviaremos un código OTP de 6 dígitos para validar tu identidad.
                  </p>

                  <div className="balam-form-group">
                    <label>Correo Electrónico</label>
                    <input 
                      type="email" 
                      placeholder="ejemplo@correo.com" 
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      disabled={otpRequested || regLoading}
                    />
                  </div>

                  {!otpRequested ? (
                    <button 
                      className="balam-primary-btn" 
                      style={{ width: '100%', marginTop: '10px' }}
                      onClick={handleRequestOtp}
                      disabled={regLoading || !regEmail.trim()}
                    >
                      {regLoading ? 'Enviando OTP...' : 'Enviar Código OTP'}
                    </button>
                  ) : (
                    <div>
                      <div className="balam-form-group" style={{ marginTop: '10px' }}>
                        <label>Código de Verificación (OTP)</label>
                        <input 
                          type="text" 
                          placeholder="Ingresa el código de 6 dígitos" 
                          maxLength={6}
                          value={regOtp}
                          onChange={(e) => setRegOtp(e.target.value)}
                          disabled={regLoading}
                        />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '14px' }}>
                        <button 
                          style={{ background: 'transparent', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '13px' }}
                          onClick={() => { setOtpRequested(false); setRegOtp(''); }}
                          disabled={regLoading}
                        >
                          Cambiar correo
                        </button>
                        <button 
                          style={{ background: 'transparent', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '13px' }}
                          onClick={handleRequestOtp}
                          disabled={regLoading}
                        >
                          Reenviar código
                        </button>
                      </div>
                      <button 
                        className="balam-primary-btn" 
                        style={{ width: '100%', marginTop: '20px' }}
                        onClick={handleVerifyOtp}
                        disabled={regLoading || regOtp.length < 6}
                      >
                        {regLoading ? 'Verificando...' : 'Verificar Código'}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 2: Shop Details */}
              {regStep === 2 && (
                <div>
                  <h3 style={{ color: 'white', fontSize: '18px', marginBottom: '12px' }}>Paso 2: Datos de la Barbería y Administrador</h3>
                  
                  <div className="balam-form-row">
                    <div className="balam-form-group">
                      <label>Nombre de la Barbería</label>
                      <input 
                        type="text" 
                        placeholder="Ej. Balam Premium Club"
                        value={regShopName}
                        onChange={(e) => setRegShopName(e.target.value)}
                      />
                    </div>
                    <div className="balam-form-group">
                      <label>Teléfono de Contacto</label>
                      <input 
                        type="text" 
                        placeholder="Ej. 961 123 4567"
                        value={regPhone}
                        onChange={(e) => setRegPhone(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="balam-form-group">
                    <label>Dirección Física</label>
                    <input 
                      type="text" 
                      placeholder="Calle, Número, Colonia, Ciudad"
                      value={regAddress}
                      onChange={(e) => setRegAddress(e.target.value)}
                    />
                  </div>

                  <div className="balam-form-row">
                    <div className="balam-form-group">
                      <label>Nombre del Propietario (Admin)</label>
                      <input 
                        type="text" 
                        placeholder="Tu nombre completo"
                        value={regOwnerName}
                        onChange={(e) => setRegOwnerName(e.target.value)}
                      />
                    </div>
                    <div className="balam-form-group">
                      <label>Contraseña de Acceso</label>
                      <input 
                        type="password" 
                        placeholder="Contraseña segura"
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="balam-form-group">
                    <label>Imagen de Portada (URL)</label>
                    <input 
                      type="text" 
                      placeholder="https://images.unsplash.com/... (Opcional)"
                      value={regImageUrl}
                      onChange={(e) => setRegImageUrl(e.target.value)}
                    />
                  </div>

                  <div className="balam-form-group">
                    <label>Descripción del Negocio</label>
                    <textarea 
                      placeholder="Cuéntale a tus clientes sobre tu barbería, especialidades, estilo..."
                      rows={2}
                      value={regDescription}
                      onChange={(e) => setRegDescription(e.target.value)}
                    />
                  </div>

                  <div className="balam-form-group">
                    <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>Ubicación en el Mapa (Haz clic para apuntar el marcador)</span>
                      <button 
                        type="button" 
                        className="balam-secondary-btn"
                        style={{ margin: 0, padding: '4px 10px', fontSize: '11px', borderRadius: '6px' }}
                        onClick={handleLocateRegistration}
                      >
                        📍 Detectar mi ubicación
                      </button>
                    </label>
                    
                    <div 
                      id="mini-map-container" 
                      className="balam-mini-map"
                    />
                    
                    <span style={{ fontSize: '11px', color: 'var(--balam-text-soft)', textAlign: 'left', display: 'block', marginTop: '6px' }}>
                      {regLatitude && regLongitude ? `Coordenadas: Lat ${regLatitude.toFixed(6)}, Lon ${regLongitude.toFixed(6)}` : '⚠️ Por favor apunta tu ubicación haciendo clic en el mapa o detectando tu GPS.'}
                    </span>
                  </div>

                  <div className="balam-wizard-footer">
                    <button className="secondary" onClick={() => setRegStep(1)}>Atrás</button>
                    <button 
                      className="primary" 
                      onClick={() => {
                        if (!regShopName.trim() || !regPhone.trim() || !regAddress.trim() || !regOwnerName.trim() || !regPassword.trim() || !regDescription.trim()) {
                          setRegError('Por favor completa todos los campos requeridos.');
                          return;
                        }
                        if (!regLatitude || !regLongitude) {
                          setRegError('Por favor selecciona la ubicación de tu barbería en el mapa.');
                          return;
                        }
                        setRegError('');
                        setRegStep(3);
                      }}
                    >
                      Siguiente
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 3: Plan Selection */}
              {regStep === 3 && (
                <div>
                  <h3 style={{ color: 'white', fontSize: '18px', marginBottom: '12px' }}>Paso 3: Selecciona tu Plan de Suscripción</h3>
                  
                  <div className="balam-plans-grid">
                    <div 
                      className={`balam-plan-card ${regPlan === 'normal' ? 'selected' : ''}`}
                      onClick={() => setRegPlan('normal')}
                    >
                      <h3>Plan Normal</h3>
                      <div className="balam-plan-price">$300 <span>MXN/mes</span></div>
                      <ul className="balam-plan-features">
                        <li>Alta en el directorio general</li>
                        <li>Marcador estándar en el mapa</li>
                        <li>Asistente virtual de AI básico</li>
                        <li>Gestión de citas automatizada</li>
                      </ul>
                    </div>

                    <div 
                      className={`balam-plan-card pro ${regPlan === 'pro' ? 'selected' : ''}`}
                      onClick={() => setRegPlan('pro')}
                    >
                      <div className="balam-plan-badge">Popular / Destacado</div>
                      <h3>Plan Pro</h3>
                      <div className="balam-plan-price">$700 <span>MXN/mes</span></div>
                      <ul className="balam-plan-features">
                        <li>Aparición en primera plana destacado</li>
                        <li>Marcador destacado en mapa</li>
                        <li>Asistente virtual de AI prioritario</li>
                        <li>Soporte de Inteligencia Artificial pro</li>
                      </ul>
                    </div>
                  </div>

                  <div className="balam-wizard-footer">
                    <button className="secondary" onClick={() => setRegStep(2)}>Atrás</button>
                    <button 
                      className="primary" 
                      onClick={() => {
                        setRegStep(4);
                      }}
                    >
                      Continuar al Pago
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 4: Payment */}
              {regStep === 4 && (
                <div>
                  <h3 style={{ color: 'white', fontSize: '18px', marginBottom: '12px' }}>Paso 4: Completa tu suscripción</h3>
                  <p style={{ color: 'var(--balam-text-soft)', fontSize: '14px', marginBottom: '16px', lineHeight: '1.5', textAlign: 'left' }}>
                    Estás por suscribirte al <strong>Plan {regPlan === 'pro' ? 'Pro' : 'Normal'}</strong> por un costo de <strong>${regPlan === 'pro' ? '700.00' : '300.00'} MXN al mes</strong>.
                  </p>

                  <div className="balam-paypal-container">
                    <div id="paypal-button-container" style={{ width: '100%', minHeight: '120px' }}></div>
                    {regLoading && <div style={{ color: 'white', marginTop: '10px', fontSize: '13px' }}>Guardando tu registro y capturando pago en la base de datos...</div>}
                  </div>

                  <div className="balam-wizard-footer">
                    <button className="secondary" onClick={() => setRegStep(3)} disabled={regLoading}>Atrás</button>
                  </div>
                </div>
              )}

              {/* STEP 5: Success */}
              {regStep === 5 && (
                <div className="balam-success-view">
                  <div className="balam-success-icon">✓</div>
                  <h3>¡Barbería Registrada Exitosamente!</h3>
                  <p>
                    El pago del plan <strong>{regPlan.toUpperCase()}</strong> ha sido capturado correctamente. Tu barbería <strong>{regShopName}</strong> ya está activa y visible en la plataforma Balam.
                  </p>
                  <p style={{ fontSize: '12px' }}>
                    Puedes ingresar al sistema administrativo usando tu correo <strong>{regEmail}</strong> y la contraseña registrada.
                  </p>
                  <button 
                    className="balam-primary-btn" 
                    style={{ width: '200px', marginTop: '20px' }}
                    onClick={resetRegistrationState}
                  >
                    Entendido
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default App
