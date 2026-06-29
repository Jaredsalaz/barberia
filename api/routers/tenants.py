from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
import math
from ..core.db import get_session
from ..schemas.tenant import Tenant
from ..schemas.barber import Barber
from ..schemas.service import Service

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en kilómetros entre dos puntos geográficos usando la fórmula del Haversine."""
    R = 6371.0 # Radio de la Tierra en km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@router.get("/")
def get_tenants(
    featured: Optional[bool] = Query(None, description="Filtrar solo barberías destacadas/anunciadas"),
    lat: Optional[float] = Query(None, description="Latitud actual del usuario"),
    lon: Optional[float] = Query(None, description="Longitud actual del usuario"),
    db_session: Session = Depends(get_session)
):
    """
    Obtiene la lista de barberías dadas de alta en la plataforma.
    Si se proporcionan coordenadas, calcula la distancia y ordena por proximidad.
    """
    from datetime import datetime
    statement = select(Tenant).where(
        Tenant.is_active == True,
        (Tenant.subscription_expires_at == None) | (Tenant.subscription_expires_at >= datetime.utcnow())
    )
    if featured is not None:
        statement = statement.where(Tenant.is_featured == featured)
        
    tenants = db_session.exec(statement).all()
    results = []
    
    for t in tenants:
        tenant_dict = {
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "phone": t.phone,
            "address": t.address,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "is_featured": t.is_featured,
            "image_url": t.image_url,
            "description": t.description,
            "business_hours": t.business_hours,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        
        # Calcular distancia si se proporcionaron coordenadas
        if lat is not None and lon is not None and t.latitude is not None and t.longitude is not None:
            dist = calculate_haversine_distance(lat, lon, t.latitude, t.longitude)
            tenant_dict["distance_km"] = round(dist, 2)
        else:
            tenant_dict["distance_km"] = None
            
        results.append(tenant_dict)
        
    # Ordenar por distancia si está disponible, si no, colocar destacados al inicio
    if lat is not None and lon is not None:
        results.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"]))
    else:
        results.sort(key=lambda x: not x["is_featured"])
        
    return results

@router.get("/{slug}")
def get_tenant_details(
    slug: str,
    db_session: Session = Depends(get_session)
):
    """
    Obtiene los detalles completos de una barbería por su slug,
    incluyendo su catálogo de servicios y barberos disponibles.
    """
    from datetime import datetime
    tenant = db_session.exec(
        select(Tenant).where(
            Tenant.slug == slug,
            Tenant.is_active == True,
            (Tenant.subscription_expires_at == None) | (Tenant.subscription_expires_at >= datetime.utcnow())
        )
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Barbería no encontrada o suscripción vencida")
        
    # Obtener barberos de esta sucursal
    barbers = db_session.exec(select(Barber).where(Barber.tenant_id == tenant.id, Barber.is_active == True)).all()
    barbers_list = [{"id": str(b.id), "name": b.name, "email": b.email} for b in barbers]
    
    # Obtener servicios
    services = db_session.exec(select(Service).where(Service.tenant_id == tenant.id, Service.is_active == True)).all()
    services_list = [{"id": str(s.id), "name": s.name, "price": s.price, "duration_minutes": s.duration_minutes} for s in services]
    
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "phone": tenant.phone,
        "address": tenant.address,
        "latitude": tenant.latitude,
        "longitude": tenant.longitude,
        "is_featured": tenant.is_featured,
        "image_url": tenant.image_url,
        "description": tenant.description,
        "business_hours": tenant.business_hours,
        "barbers": barbers_list,
        "services": services_list
    }
