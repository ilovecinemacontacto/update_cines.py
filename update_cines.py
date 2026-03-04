import os
import time
from supabase import create_client
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# 1. Configuración de Supabase (usando Variables de Entorno)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# 2. Configurar el buscador (Nominatim)
# Es obligatorio poner un user_agent único
geolocator = Nominatim(user_agent="my_cinema_bot_espana_2024")

def buscar_direccion_osm(nombre, ciudad):
    query = f"{nombre}, {ciudad}, España"
    try:
        # Buscamos la localización
        location = geolocator.geocode(query, addressdetails=True, timeout=10)
        if location:
            return location.address
        return None
    except GeocoderTimedOut:
        return None

# 3. Proceso principal
def main():
    # Obtenemos los cines donde la dirección es nula
    # Limitamos a 50 por ejecución para no saturar y que GitHub no nos corte
    response = supabase.table("cines").select("id, nombre, ciudad").is_("direccion", "null").limit(50).execute()
    cines = response.data

    if not cines:
        print("No hay cines pendientes de dirección.")
        return

    for cine in cines:
        print(f"Buscando: {cine['nombre']} en {cine['ciudad']}...")
        
        direccion = buscar_direccion_osm(cine['nombre'], cine['ciudad'])
        
        if direccion:
            supabase.table("cines").update({"direccion": direccion}).eq("id", cine['id']).execute()
            print(f"✅ Encontrado: {direccion}")
        else:
            print(f"❌ No se pudo encontrar la dirección exacta.")
        
        # IMPORTANTE: Nominatim requiere máximo 1 petición por segundo
        time.sleep(1.5)

if __name__ == "__main__":
    main()
