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
        'Abulug', 'Aglipay', 'Alcala', 'Alfonso Castañeda', 'Alicia', 'Allacapan', 'Ambaguio', 'Amulung', 'Angadanan', 'Aparri', 'Aritao', 'Aurora', 'Bagabag', 'Baggao', 'Ballesteros', 'Bambang', 'Basco', 'Bayombong', 'Benito Soliven', 'Buguey', 'Burgos', 'Cabagan', 'Cabarroguis', 'Cabatuan', 'Calayan',
          'Camalaniugan', 'Claveria', 'Cordon', 'Delfin Albano', 'Diadi', 'Diffun', 'Dinapigue', 'Divilacan', 'Dupax del Norte', 'Dupax del Sur', 'Echague', 'Enrile', 'Gamu', 'Gattaran', 'Gonzaga', 'Iguig', 'Itbayat', 'Ivana', 'Jones', 'Kasibu'
    ],
    'REGION-III': [
        'Abucay', 'Aliaga', 'Angat', 'Ani-ao', 'Apalit', 'Arayat', 'Bacolor', 'Bagac', 'Balagtas', 'Baliuag', 'Baler', 'Bamban', 'Bangui', 'Barasoain', 'Bocaue', 'Bongabon', 'Bulakan', 'Bustos', 'Cabangan', 'Cabiao', 'Calumpit', 'Camiling', 'Candaba', 'Capas', 'Carranglan', 'Casiguran', 'Castillejos',
          'Concepcion', 'Cuyapo', 'Dalayap', 'Dilasag', 'Dinalupihan', 'Dingalan', 'Dipaculao', 'Doña Remedios Trinidad', 'Floridablanca', 'Gabaldon', 'General Mamerto Natividad', 'General Tinio', 'Gerona', 'Guagua', 'Guiguinto', 'Guimba', 'Hagonoy', 'Hermosa', 'Iba','Ivana', 'Jones', 'Kasibu'

    ],
    'REGION-IV-A': [
        'Agdangan', 'Agoncillo', 'Alabat', 'Alaminos', 'Alfonso', 'Alitagtag', 'Amadeo', 'Angono', 'Atimonan', 'Balayan', 'Balete', 'Baras', 'Bauan', 'Bay', 'Binangonan', 'Buenavista', 'Burdeos', 'Cainta', 'Calatagan', 'Calauag', 'Calauan', 'Candelaria', 'Cardona', 'Catanauan', 'Cavinti', 'Cuenca', 'Dolores',
          'Famy', 'General Emilio Aguinaldo', 'General Luna', 'General Mariano Alvarez', 'General Nakar', 'Guinayangan', 'Gumaca', 'Ibaan', 'Indang', 'Infanta', 'Jalajala', 'Jomalig', 'Kalayaan', 'Kawit', 'Laurel', 'Lemery', 'Lian', 'Liliw', 'Lobo', 'Lopez', 'Los Baños', 'Lucban', 'Luisiana', 'Lumban', 'Mabini',
            'Mabitac', 'Macalelon', 'Magallanes', 'Magdalena', 'Majayjay', 'Malvar', 'Maragondon', 'Mataasnakahoy', 'Mauban', 'Mendez', 'Morong', 'Mulanay', 'Nagcarlan', 'Naic', 'Nasugbu', 'Noveleta', 'Padre Burgos', 'Padre Garcia', 'Paete', 'Pagbilao', 'Pagsanjan', 'Pakil', 'Pangil', 'Panukulan', 'Patnanungan',
              'Perez', 'Pila', 'Pililla', 'Pitogo', 'Plaridel', 'Polillo', 'Quezon', 'Real', 'Rizal', 'Rodriguez', 'Rosario', 'Sampaloc', 'San Andres', 'San Antonio', 'San Francisco', 'San Jose', 'San Juan', 'San Luis', 'San Mateo', 'San Narciso', 'San Nicolas', 'San Pascual', 'Santa Cruz', 'Santa Maria', 'Santa Teresita',
                'Sariaya', 'Silang', 'Siniloan', 'Taal', 'Tagkawayan', 'Talisay', 'Tanay', 'Tanza', 'Taysan', 'Taytay', 'Teresa', 'Ternate', 'Tiaong', 'Tingloy', 'Tuy', 'Unisan', 'Victoria'
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
