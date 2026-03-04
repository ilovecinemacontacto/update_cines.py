import os
import time
import re
from supabase import create_client
from geopy.geocoders import Nominatim

# 1. Configuración
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)
geolocator = Nominatim(user_agent="bot_cines_espana_ultra_v3")

def limpiar_nombre(nombre):
    """Limpia el nombre del cine para facilitar la búsqueda"""
    # 1. Quitar todo lo que esté entre paréntesis (ej: Cine de Verano)
    nombre = re.sub(r'\(.*?\)', '', nombre)
    # 2. Quitar términos legales o innecesarios
    palabras_ruido = ['S.A.', 'S.L.', 'S.A.U.', 'MULTICINES', 'CINES', 'CINE']
    for ruido in palabras_ruido:
        nombre = nombre.replace(ruido, '')
    # 3. Quitar espacios extra
    return nombre.strip()

def buscar_direccion_ultra(nombre, provincia):
    nombre_limpio = limpiar_nombre(nombre)
    
    # Intentos en cascada: de lo más específico a lo más general
    queries = [
        f"{nombre_limpio}, {provincia}, España", # Ej: "Liceo, Cordoba, España"
        f"{nombre}, {provincia}, España",        # Por si el nombre original era mejor
        f"{nombre_limpio} {provincia}",          # Búsqueda libre
    ]
    
    # Si el nombre es muy largo, intentamos solo con las 3 primeras palabras
    palabras = nombre_limpio.split()
    if len(palabras) > 3:
        queries.append(f"{' '.join(palabras[:3])} {provincia} España")

    for query in queries:
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                return location.address
        except:
            continue
        time.sleep(0.5) # Micro-pausa entre re-intentos de un mismo cine
    return None

def main():
    # Seguimos con límite de 200 para evitar bloqueos por IP
    response = supabase.table("cines").select("id, nombre, ciudad").is_("direccion", "null").limit(200).execute()
    cines = response.data

    if not cines:
        print("No hay más cines por procesar.")
        return

    for cine in cines:
        print(f"Probando con: {cine['nombre']}...")
        direccion = buscar_direccion_ultra(cine['nombre'], cine['ciudad'])
        
        if direccion:
            supabase.table("cines").update({"direccion": direccion}).eq("id", cine['id']).execute()
            print(f"✅ ¡ÉXITO!: {direccion[:60]}...")
        else:
            # MARCAMOS COMO 'FALLIDO' para no re-intentar el mismo 1000 veces
            # Esto es vital para que el bot avance a los siguientes
            supabase.table("cines").update({"direccion": "Revision Manual"}).eq("id", cine['id']).execute()
            print(f"❌ FALLO")
        
        time.sleep(1.2) # Respetar límite de Nominatim

if __name__ == "__main__":
    main()
