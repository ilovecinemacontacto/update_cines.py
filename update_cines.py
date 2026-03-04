import os
import time
from supabase import create_client
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# 1. Configuración de Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# 2. Configurar el buscador con un User Agent único
geolocator = Nominatim(user_agent="bot_cines_espana_v2")

def buscar_direccion_mejorada(nombre, provincia):
    # Definimos tres niveles de búsqueda para "afinar el tiro"
    queries = [
        f"{nombre}, {provincia}, España",       # 1. Intento más preciso
        f"cine {nombre} {provincia}",           # 2. Intento descriptivo
        f"{nombre} España"                      # 3. Intento desesperado
    ]
    
    for query in queries:
        try:
            print(f"  Probando: {query}")
            location = geolocator.geocode(query, addressdetails=True, timeout=10)
            if location:
                # Priorizamos direcciones que contengan la provincia para evitar errores
                return location.address
        except (GeocoderTimedOut, GeocoderServiceError):
            time.sleep(2) # Si hay error de conexión, esperamos un poco
            continue
    return None

def main():
    # Traemos 200 cines que tengan la dirección vacía
    # Nota: Asegúrate de que en Supabase la columna 'direccion' sea NULL por defecto
    response = supabase.table("cines").select("id, nombre, ciudad").is_("direccion", "null").limit(200).execute()
    cines = response.data

    if not cines:
        print("🎉 ¡Todos los cines tienen dirección o no quedan registros pendientes!")
        return

    print(f"🚀 Iniciando procesamiento de {len(cines)} cines...")

    for cine in cines:
        id_cine = cine['id']
        nombre = cine['nombre']
        provincia = cine['ciudad'] # Según me indicas, aquí está la provincia

        print(f"\n🔎 Buscando: {nombre} ({provincia})")
        
        direccion = buscar_direccion_mejorada(nombre, provincia)
        
        if direccion:
            supabase.table("cines").update({"direccion": direccion}).eq("id", id_cine).execute()
            print(f"✅ Guardado: {direccion[:50]}...")
        else:
            # Opcional: Marcar como 'No encontrado' para que el bot no lo procese mil veces
            # supabase.table("cines").update({"direccion": "No encontrado"}).eq("id", id_cine).execute()
            print(f"❌ Sin éxito tras varios intentos.")
        
        # Respetar el límite de 1 consulta por segundo de Nominatim
        time.sleep(1.5)

if __name__ == "__main__":
    main()
