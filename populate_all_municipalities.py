import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase app
cred = credentials.Certificate('firebase-credentials.json')
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Philippine regions and their municipalities (abbreviated for brevity; expand as needed)
regions_municipalities = {
    'REGION-I': [
        'Adams', 'Bacarra', 'Badoc', 'Bangui', 'Banna', 'Batac City', 'Burgos', 'Carasi', 'Currimao', 'Dingras', 'Dumalneg', 'Laoag City', 'Marcos', 'Nueva Era', 'Pagudpud', 'Paoay', 'Pasuquin', 'Piddig', 'Pinili', 'San Nicolas', 'Sarrat', 'Solsona', 'Vintar',
        # ...add all municipalities for Ilocos Norte, Ilocos Sur, La Union, Pangasinan
    ],
    'REGION-II': [
        # ...add all municipalities for Cagayan Valley
    ],
    'REGION-III': [
        # ...add all municipalities for Central Luzon
    ],
    'REGION-IV-A': [
        # ...add all municipalities for CALABARZON
    ],
    'REGION-IV-B': [
        'Abra de Ilog', 'Calintaan', 'Looc', 'Lubang', 'Magsaysay', 'Mamburao', 'Paluan', 'Rizal', 'Sablayan', 'San Jose', 'Santa Cruz',
        'Baco', 'Bansud', 'Bongabong', 'Bulalacao', 'Gloria', 'Mansalay', 'Naujan', 'Pinamalayan', 'Pola', 'Puerto Galera', 'Roxas', 'San Teodoro', 'Socorro', 'Victoria',
        'Boac', 'Buenavista', 'Gasan', 'Mogpog', 'Santa Cruz', 'Torrijos',
        'Alcantara', 'Banton', 'Cajidiocan', 'Calatrava', 'Concepcion', 'Corcuera', 'Ferrol', 'Looc', 'Magdiwang', 'Odiongan', 'Romblon', 'San Agustin', 'San Andres', 'San Fernando', 'San Jose', 'Santa Fe', 'Santa Maria',
        'Aborlan', 'Agutaya', 'Araceli', 'Balabac', 'Bataraza', 'Brooke’s Point', 'Busuanga', 'Cagayancillo', 'Coron', 'Culion', 'Cuyo', 'Dumaran', 'El Nido', 'Kalayaan', 'Linapacan', 'Magsaysay', 'Narra', 'Puerto Princesa City', 'Quezon', 'Rizal', 'Roxas', 'San Vicente', 'Sofronio Española', 'Taytay'
    ],
    # ...add all other regions (V, VI, VII, VIII, IX, X, XI, XII, XIII, BARMM, NCR, CAR, CARAGA)
}

for region, municipalities in regions_municipalities.items():
    doc_ref = db.collection('municipalities').document(region)
    doc_ref.set({'municipalities': municipalities})
    print(f"Municipalities for {region} set in Firestore.")
