"""O atlas das animações: lugares com coordenadas, para o mapa-múndi pôr o ponto no lugar certo.

Do estudo da Dotti (2026-11-22): o mapa dela acende o ponto certo no mundo e traça a rota entre dois lugares. O
nosso `mapa` só escrevia o nome. Este atlas foi escrito aqui, à mão: países (no centro aproximado), capitais e as
cidades mais citadas, com os nomes em inglês, português e espanhol (e alguns apelidos). As coordenadas são
aproximadas, de propósito: o mapa é estilizado, sem fronteiras, e erra no máximo alguns décimos de grau.

Cada linha: latitude, longitude, tipo (p = país, c = cidade, r = região) e os nomes separados por "|".
Os contornos dos continentes (CONTINENTES) são polígonos de poucos pontos, para o desenho "low poly" do mapa.
"""
import math
import re
import unicodedata

_ATLAS = """
-33.9,18.4,c,Cape Town|Cidade do Cabo|Ciudad del Cabo
-34.6,-58.4,c,Buenos Aires
-33.4,-70.6,c,Santiago|Santiago do Chile|Santiago de Chile
-23.5,-46.6,c,São Paulo|Sao Paulo
-22.9,-43.2,c,Rio de Janeiro|Rio
-15.8,-47.9,c,Brasília|Brasilia
-12.0,-77.0,c,Lima
4.7,-74.1,c,Bogotá|Bogota
10.5,-66.9,c,Caracas
-0.2,-78.5,c,Quito
-16.5,-68.1,c,La Paz
-25.3,-57.6,c,Asunción|Assunção|Asuncion
-34.9,-56.2,c,Montevideo|Montevidéu
-3.1,-60.0,c,Manaus
-12.97,-38.5,c,Salvador
-8.05,-34.9,c,Recife
-3.7,-38.5,c,Fortaleza
-30.0,-51.2,c,Porto Alegre
-25.4,-49.3,c,Curitiba
-19.9,-43.9,c,Belo Horizonte
-1.5,-48.5,c,Belém|Belem
19.4,-99.1,c,Mexico City|Cidade do México|Ciudad de México|Ciudad de Mexico
20.7,-103.3,c,Guadalajara
25.7,-100.3,c,Monterrey
21.2,-86.8,c,Cancún|Cancun
23.1,-82.4,c,Havana|Havana|La Habana
18.5,-69.9,c,Santo Domingo
18.5,-72.3,c,Port-au-Prince|Porto Príncipe|Puerto Príncipe
14.6,-90.5,c,Guatemala City|Cidade da Guatemala|Ciudad de Guatemala
9.0,-79.5,c,Panama City|Cidade do Panamá|Ciudad de Panamá
9.9,-84.1,c,San José
40.7,-74.0,c,New York|Nova York|Nueva York|NYC|New York City|Manhattan
34.05,-118.24,c,Los Angeles|Los Ángeles|LA
41.9,-87.6,c,Chicago
29.8,-95.4,c,Houston
33.4,-112.1,c,Phoenix
39.95,-75.17,c,Philadelphia|Filadélfia|Filadelfia
29.4,-98.5,c,San Antonio
32.7,-117.2,c,San Diego
32.8,-96.8,c,Dallas
37.3,-121.9,c,San Jose
30.3,-97.7,c,Austin
37.77,-122.42,c,San Francisco|São Francisco
47.6,-122.3,c,Seattle
39.7,-105.0,c,Denver
38.9,-77.0,c,Washington|Washington D.C.|Washington DC
42.36,-71.06,c,Boston
25.8,-80.2,c,Miami
33.75,-84.39,c,Atlanta
36.17,-115.14,c,Las Vegas
42.33,-83.05,c,Detroit
45.5,-122.7,c,Portland
36.16,-86.78,c,Nashville
29.95,-90.07,c,New Orleans|Nova Orleans|Nueva Orleans
21.3,-157.8,c,Honolulu
61.2,-149.9,c,Anchorage
37.4,-122.1,r,Silicon Valley|Vale do Silício|Silicon Valley|Valle del Silicio
36.8,-119.4,r,California|Califórnia
27.8,-81.7,r,Florida|Flórida
43.0,-75.0,r,New York State|Estado de Nova York
31.0,-100.0,r,Texas
64.2,-149.5,r,Alaska
19.9,-155.6,r,Hawaii|Havaí|Hawái
43.65,-79.38,c,Toronto
45.5,-73.6,c,Montreal|Montréal
49.28,-123.12,c,Vancouver
45.42,-75.7,c,Ottawa
51.05,-114.07,c,Calgary
51.5,-0.13,c,London|Londres
48.86,2.35,c,Paris
52.52,13.4,c,Berlin|Berlim|Berlín
40.42,-3.7,c,Madrid
41.39,2.17,c,Barcelona
38.72,-9.14,c,Lisbon|Lisboa
41.15,-8.61,c,Porto|Oporto
41.9,12.5,c,Rome|Roma
45.46,9.19,c,Milan|Milão|Milán
45.44,12.33,c,Venice|Veneza|Venecia
40.85,14.27,c,Naples|Nápoles
43.77,11.25,c,Florence|Florença|Florencia
41.9,12.45,c,Vatican City|Vaticano|Ciudad del Vaticano|Vatican
52.37,4.9,c,Amsterdam|Amsterdã|Ámsterdam
50.85,4.35,c,Brussels|Bruxelas|Bruselas
48.21,16.37,c,Vienna|Viena
47.37,8.54,c,Zurich|Zurique|Zúrich
46.2,6.15,c,Geneva|Genebra|Ginebra
50.08,14.44,c,Prague|Praga
47.5,19.04,c,Budapest|Budapeste
52.23,21.01,c,Warsaw|Varsóvia|Varsovia
59.33,18.07,c,Stockholm|Estocolmo
59.91,10.75,c,Oslo
55.68,12.57,c,Copenhagen|Copenhague
60.17,24.94,c,Helsinki|Helsinque
64.15,-21.94,c,Reykjavik|Reykjavík|Reiquiavique
53.35,-6.26,c,Dublin|Dublim|Dublín
55.95,-3.19,c,Edinburgh|Edimburgo
53.48,-2.24,c,Manchester
53.41,-2.98,c,Liverpool
37.98,23.73,c,Athens|Atenas
41.01,28.98,c,Istanbul|Istambul|Estambul|Constantinople|Constantinopla
39.93,32.86,c,Ankara|Ancara
55.76,37.62,c,Moscow|Moscou|Moscú
59.94,30.31,c,Saint Petersburg|São Petersburgo|San Petersburgo
50.45,30.52,c,Kyiv|Kiev|Kiev
44.43,26.1,c,Bucharest|Bucareste|Bucarest
42.7,23.32,c,Sofia
44.82,20.46,c,Belgrade|Belgrado
45.81,15.98,c,Zagreb
43.3,5.37,c,Marseille|Marselha|Marsella
45.76,4.84,c,Lyon|Lião
48.14,11.58,c,Munich|Munique|Múnich
50.11,8.68,c,Frankfurt|Frankfurt|Fráncfort
53.55,9.99,c,Hamburg|Hamburgo
37.39,-5.98,c,Seville|Sevilha|Sevilla
43.74,7.42,c,Monaco|Mônaco|Mónaco|Monte Carlo
36.14,-5.35,c,Gibraltar
35.9,14.5,c,Valletta|Valeta
30.04,31.24,c,Cairo|Cairo|El Cairo
31.2,29.92,c,Alexandria|Alexandria|Alejandría
29.98,31.13,c,Giza|Gizé|Guiza
33.57,-7.59,c,Casablanca
34.02,-6.84,c,Rabat
31.63,-8.0,c,Marrakesh|Marrakech|Marraquexe
36.8,10.18,c,Tunis|Túnis|Túnez
36.75,3.06,c,Algiers|Argel
32.89,13.19,c,Tripoli|Trípoli
6.52,3.38,c,Lagos
9.06,7.49,c,Abuja
5.6,-0.19,c,Accra|Acra
14.69,-17.44,c,Dakar|Dacar
-1.29,36.82,c,Nairobi
9.03,38.74,c,Addis Ababa|Adis Abeba|Adís Abeba
-6.79,39.21,c,Dar es Salaam
-26.2,28.05,c,Johannesburg|Joanesburgo|Johannesburgo
-25.75,28.19,c,Pretoria|Pretória
-4.32,15.31,c,Kinshasa|Quinxassa
-8.84,13.23,c,Luanda
-25.97,32.57,c,Maputo
0.35,32.58,c,Kampala|Campala
15.5,32.56,c,Khartoum|Cartum|Jartum
2.04,45.34,c,Mogadishu|Mogadíscio|Mogadiscio
-18.9,47.5,c,Antananarivo
31.77,35.21,c,Jerusalem|Jerusalém|Jerusalén
32.09,34.78,c,Tel Aviv
33.89,35.5,c,Beirut|Beirute
33.51,36.28,c,Damascus|Damasco
31.95,35.93,c,Amman|Amã|Amán
33.31,44.36,c,Baghdad|Bagdá|Bagdad
35.69,51.39,c,Tehran|Teerã|Teherán
24.71,46.68,c,Riyadh|Riad|Riad
21.39,39.86,c,Mecca|Meca|La Meca
21.49,39.19,c,Jeddah|Jidá|Yeda
25.2,55.27,c,Dubai|Dubai|Dubái
24.45,54.38,c,Abu Dhabi|Abu Dhabi|Abu Dabi
25.29,51.53,c,Doha
29.38,47.99,c,Kuwait City|Cidade do Kuwait|Ciudad de Kuwait
23.59,58.38,c,Muscat|Mascate
15.37,44.19,c,Sanaa|Saná
34.53,69.17,c,Kabul|Cabul|Kabul
33.69,73.04,c,Islamabad|Islamabade
24.86,67.0,c,Karachi|Carachi
31.55,74.34,c,Lahore
28.61,77.21,c,New Delhi|Nova Délhi|Nueva Delhi|Delhi|Délhi
19.08,72.88,c,Mumbai|Bombaim|Bombay
12.97,77.59,c,Bangalore|Bengaluru
13.08,80.27,c,Chennai|Madras
22.57,88.36,c,Kolkata|Calcutá|Calcuta
17.39,78.49,c,Hyderabad
23.81,90.41,c,Dhaka|Daca|Daca
27.72,85.32,c,Kathmandu|Katmandu|Katmandú
6.93,79.86,c,Colombo
39.9,116.4,c,Beijing|Pequim|Pekín|Peking
31.23,121.47,c,Shanghai|Xangai|Shanghái
22.54,114.06,c,Shenzhen
23.13,113.26,c,Guangzhou|Cantão|Cantón
22.32,114.17,c,Hong Kong
22.2,113.54,c,Macau|Macau|Macao
30.57,104.07,c,Chengdu
29.56,106.55,c,Chongqing
30.59,114.31,c,Wuhan
34.34,108.94,c,Xi'an|Xian
25.03,121.57,c,Taipei|Taipé|Taipéi
37.57,126.98,c,Seoul|Seul|Seúl
35.18,129.08,c,Busan
39.02,125.75,c,Pyongyang|Pyongyang|Pionyang
35.68,139.69,c,Tokyo|Tóquio|Tokio
34.69,135.5,c,Osaka
35.01,135.77,c,Kyoto|Quioto|Kioto
34.39,132.46,c,Hiroshima
32.75,129.88,c,Nagasaki
43.06,141.35,c,Sapporo
13.76,100.5,c,Bangkok|Bangkok|Bangkok
21.03,105.85,c,Hanoi|Hanói
10.82,106.63,c,Ho Chi Minh City|Cidade de Ho Chi Minh|Ciudad Ho Chi Minh|Saigon|Saigão
11.56,104.92,c,Phnom Penh
16.87,96.2,c,Yangon|Rangum|Rangún
3.14,101.69,c,Kuala Lumpur
1.35,103.82,c,Singapore|Singapura|Singapur
-6.21,106.85,c,Jakarta|Jacarta|Yakarta
-8.65,115.22,r,Bali
14.6,120.98,c,Manila
-33.87,151.21,c,Sydney|Sidney|Sídney
-37.81,144.96,c,Melbourne
-27.47,153.03,c,Brisbane
-31.95,115.86,c,Perth
-35.28,149.13,c,Canberra
-36.85,174.76,c,Auckland
-41.29,174.78,c,Wellington
47.92,106.92,c,Ulaanbaatar|Ulan Bator|Ulán Bator
43.24,76.89,c,Almaty
51.17,71.43,c,Astana
41.3,69.24,c,Tashkent|Tashkent|Taskent
40.41,49.87,c,Baku
41.72,44.79,c,Tbilisi
40.18,44.51,c,Yerevan|Erevan|Ereván
53.9,27.57,c,Minsk
54.69,25.28,c,Vilnius
56.95,24.11,c,Riga
59.44,24.75,c,Tallinn
-17.83,31.05,c,Harare
-15.42,28.28,c,Lusaka
12.37,-1.52,c,Ouagadougou|Uagadugu
12.64,-8.0,c,Bamako
16.77,-3.0,c,Timbuktu|Tombuctu|Tombuctú
-0.95,-90.97,r,Galápagos|Galapagos|Galápagos Islands|Ilhas Galápagos|Islas Galápagos
-27.1,-109.4,r,Easter Island|Ilha de Páscoa|Isla de Pascua|Rapa Nui
-13.16,-72.55,c,Machu Picchu
-54.8,-68.3,c,Ushuaia
27.99,86.93,r,Mount Everest|Everest|Monte Everest
-3.07,37.35,r,Kilimanjaro|Quilimanjaro
-3.47,-62.21,r,Amazon|Amazônia|Amazonia|Amazon rainforest|Floresta Amazônica|Selva amazónica
23.4,25.66,r,Sahara|Saara|Sahara Desert|Deserto do Saara|Desierto del Sahara
-90.0,0.0,r,South Pole|Polo Sul|Polo Sur
90.0,0.0,r,North Pole|Polo Norte|Polo Norte
78.2,15.6,r,Svalbard
-25.3,131.0,r,Uluru
36.1,-112.1,r,Grand Canyon|Grand Canyon|Gran Cañón
25.0,-71.0,r,Bermuda Triangle|Triângulo das Bermudas|Triángulo de las Bermudas
51.18,-1.83,r,Stonehenge
51.39,30.1,c,Chernobyl|Chernobil|Chernóbil
37.42,141.03,c,Fukushima
40.75,14.49,c,Pompeii|Pompeia|Pompeya
9.08,-79.68,r,Panama Canal|Canal do Panamá|Canal de Panamá
30.5,32.3,r,Suez Canal|Canal de Suez
26.57,56.25,r,Strait of Hormuz|Estreito de Ormuz|Estrecho de Ormuz
33.94,67.71,p,Afghanistan|Afeganistão|Afganistán
41.15,20.17,p,Albania|Albânia
28.03,1.66,p,Algeria|Argélia|Argelia
42.55,1.6,p,Andorra
-11.2,17.87,p,Angola
-38.42,-63.62,p,Argentina
40.07,45.04,p,Armenia|Armênia
-25.27,133.78,p,Australia|Austrália
47.52,14.55,p,Austria|Áustria
40.14,47.58,p,Azerbaijan|Azerbaijão|Azerbaiyán
25.03,-77.4,p,Bahamas
26.07,50.56,p,Bahrain|Bahrein|Baréin
23.68,90.36,p,Bangladesh
13.19,-59.54,p,Barbados
53.71,27.95,p,Belarus|Bielorrússia|Bielorrusia
50.5,4.47,p,Belgium|Bélgica
17.19,-88.5,p,Belize
9.31,2.32,p,Benin|Benim
27.51,90.43,p,Bhutan|Butão|Bután
-16.29,-63.59,p,Bolivia|Bolívia
43.92,17.68,p,Bosnia and Herzegovina|Bósnia e Herzegovina|Bosnia y Herzegovina|Bosnia
-22.33,24.68,p,Botswana|Botsuana
-14.24,-51.93,p,Brazil|Brasil
4.54,114.73,p,Brunei|Brunei|Brunéi
42.73,25.49,p,Bulgaria|Bulgária
12.24,-1.56,p,Burkina Faso
-3.37,29.92,p,Burundi
12.57,104.99,p,Cambodia|Camboja|Camboya
7.37,12.35,p,Cameroon|Camarões|Camerún
56.13,-106.35,p,Canada|Canadá
16.0,-24.0,p,Cape Verde|Cabo Verde
6.61,20.94,p,Central African Republic|República Centro-Africana|República Centroafricana
15.45,18.73,p,Chad|Chade
-35.68,-71.54,p,Chile
35.86,104.2,p,China
4.57,-74.3,p,Colombia|Colômbia
-11.88,43.87,p,Comoros|Comores|Comoras
-0.23,15.83,p,Republic of the Congo|Congo|República do Congo|República del Congo
-4.04,21.76,p,Democratic Republic of the Congo|DR Congo|República Democrática do Congo|República Democrática del Congo|RDC
9.75,-83.75,p,Costa Rica
7.54,-5.55,p,Ivory Coast|Côte d'Ivoire|Costa do Marfim|Costa de Marfil
45.1,15.2,p,Croatia|Croácia|Croacia
21.52,-77.78,p,Cuba
35.13,33.43,p,Cyprus|Chipre
49.82,15.47,p,Czech Republic|Czechia|República Tcheca|Tchéquia|República Checa|Chequia
56.26,9.5,p,Denmark|Dinamarca
11.83,42.59,p,Djibouti|Djibuti|Yibuti
18.74,-70.16,p,Dominican Republic|República Dominicana
-1.83,-78.18,p,Ecuador|Equador
26.82,30.8,p,Egypt|Egito|Egipto
13.79,-88.9,p,El Salvador
1.65,10.27,p,Equatorial Guinea|Guiné Equatorial|Guinea Ecuatorial
15.18,39.78,p,Eritrea|Eritreia
58.6,25.01,p,Estonia|Estônia
-26.52,31.47,p,Eswatini|Essuatíni|Esuatini|Swaziland
9.15,40.49,p,Ethiopia|Etiópia|Etiopía
-16.58,179.41,p,Fiji|Fiji|Fiyi
61.92,25.75,p,Finland|Finlândia|Finlandia
46.23,2.21,p,France|França|Francia
-0.8,11.61,p,Gabon|Gabão|Gabón
13.44,-15.31,p,Gambia|Gâmbia
42.32,43.36,p,Georgia (country)|Geórgia (país)
51.17,10.45,p,Germany|Alemanha|Alemania
7.95,-1.02,p,Ghana|Gana
39.07,21.82,p,Greece|Grécia|Grecia
71.71,-42.6,p,Greenland|Groenlândia|Groenlandia
15.78,-90.23,p,Guatemala
9.95,-9.7,p,Guinea|Guiné
11.8,-15.18,p,Guinea-Bissau|Guiné-Bissau
4.86,-58.93,p,Guyana|Guiana
18.97,-72.29,p,Haiti|Haití
15.2,-86.24,p,Honduras
47.16,19.5,p,Hungary|Hungria|Hungría
64.96,-19.02,p,Iceland|Islândia|Islandia
20.59,78.96,p,India|Índia
-0.79,113.92,p,Indonesia|Indonésia
32.43,53.69,p,Iran|Irã|Irán
33.22,43.68,p,Iraq|Iraque|Irak
53.41,-8.24,p,Ireland|Irlanda
31.05,34.85,p,Israel
41.87,12.57,p,Italy|Itália|Italia
18.11,-77.3,p,Jamaica
36.2,138.25,p,Japan|Japão|Japón
30.59,36.24,p,Jordan (country)|Jordânia|Jordania
48.02,66.92,p,Kazakhstan|Cazaquistão|Kazajistán
-0.02,37.91,p,Kenya|Quênia|Kenia
29.31,47.48,p,Kuwait|Kuwait
41.2,74.77,p,Kyrgyzstan|Quirguistão|Kirguistán
19.86,102.5,p,Laos
56.88,24.6,p,Latvia|Letônia|Letonia
33.85,35.86,p,Lebanon|Líbano
-29.61,28.23,p,Lesotho|Lesoto|Lesoto
6.43,-9.43,p,Liberia|Libéria
26.34,17.23,p,Libya|Líbia|Libia
47.17,9.56,p,Liechtenstein
55.17,23.88,p,Lithuania|Lituânia|Lituania
49.82,6.13,p,Luxembourg|Luxemburgo
-18.77,46.87,p,Madagascar
-13.25,34.3,p,Malawi|Malaui|Malaui
4.21,101.98,p,Malaysia|Malásia|Malasia
3.2,73.22,p,Maldives|Maldivas
17.57,-4.0,p,Mali
35.94,14.38,p,Malta
21.01,-10.94,p,Mauritania|Mauritânia
-20.35,57.55,p,Mauritius|Maurício|Mauricio
23.63,-102.55,p,Mexico|México
47.41,28.37,p,Moldova|Moldávia|Moldavia
46.86,103.85,p,Mongolia|Mongólia
42.71,19.37,p,Montenegro
31.79,-7.09,p,Morocco|Marrocos|Marruecos
-18.67,35.53,p,Mozambique|Moçambique
21.91,95.96,p,Myanmar|Mianmar|Birmania|Burma
-22.96,18.49,p,Namibia|Namíbia
28.39,84.12,p,Nepal
52.13,5.29,p,Netherlands|Holland|Holanda|Países Baixos|Países Bajos
-40.9,174.89,p,New Zealand|Nova Zelândia|Nueva Zelanda
12.87,-85.21,p,Nicaragua|Nicarágua
17.61,8.08,p,Niger|Níger
9.08,8.68,p,Nigeria|Nigéria
40.34,127.51,p,North Korea|Coreia do Norte|Corea del Norte
41.61,21.75,p,North Macedonia|Macedônia do Norte|Macedonia del Norte
60.47,8.47,p,Norway|Noruega
21.51,55.92,p,Oman|Omã|Omán
30.38,69.35,p,Pakistan|Paquistão|Pakistán
8.54,-80.78,p,Panama|Panamá
-6.31,143.96,p,Papua New Guinea|Papua-Nova Guiné|Papúa Nueva Guinea
-23.44,-58.44,p,Paraguay|Paraguai
-9.19,-75.02,p,Peru|Perú
12.88,121.77,p,Philippines|Filipinas
51.92,19.15,p,Poland|Polônia|Polonia
39.4,-8.22,p,Portugal
18.22,-66.59,p,Puerto Rico|Porto Rico
25.35,51.18,p,Qatar|Catar
45.94,24.97,p,Romania|Romênia|Rumania
61.52,105.32,p,Russia|Rússia|Rusia
-1.94,29.87,p,Rwanda|Ruanda
23.89,45.08,p,Saudi Arabia|Arábia Saudita|Arabia Saudita|Arabia Saudí
14.5,-14.45,p,Senegal
44.02,21.01,p,Serbia|Sérvia
-4.68,55.49,p,Seychelles
8.46,-11.78,p,Sierra Leone|Serra Leoa|Sierra Leona
48.67,19.7,p,Slovakia|Eslováquia|Eslovaquia
46.15,14.99,p,Slovenia|Eslovênia|Eslovenia
-9.65,160.16,p,Solomon Islands|Ilhas Salomão|Islas Salomón
5.15,46.2,p,Somalia|Somália
-30.56,22.94,p,South Africa|África do Sul|Sudáfrica
35.91,127.77,p,South Korea|Coreia do Sul|Corea del Sur|Korea|Coreia|Corea
6.88,31.31,p,South Sudan|Sudão do Sul|Sudán del Sur
40.46,-3.75,p,Spain|Espanha|España
7.87,80.77,p,Sri Lanka
12.86,30.22,p,Sudan|Sudão|Sudán
3.92,-56.03,p,Suriname|Surinam
60.13,18.64,p,Sweden|Suécia|Suecia
46.82,8.23,p,Switzerland|Suíça|Suiza
34.8,38.99,p,Syria|Síria|Siria
23.7,120.96,p,Taiwan|Taiwan|Taiwán
38.86,71.28,p,Tajikistan|Tajiquistão|Tayikistán
-6.37,34.89,p,Tanzania|Tanzânia
15.87,100.99,p,Thailand|Tailândia|Tailandia
-8.87,125.73,p,East Timor|Timor-Leste|Timor Oriental
8.62,0.82,p,Togo
10.69,-61.22,p,Trinidad and Tobago|Trinidad e Tobago|Trinidad y Tobago
33.89,9.54,p,Tunisia|Tunísia|Túnez
38.96,35.24,p,Turkey|Türkiye|Turquia|Turquía
38.97,59.56,p,Turkmenistan|Turcomenistão|Turkmenistán
1.37,32.29,p,Uganda
48.38,31.17,p,Ukraine|Ucrânia|Ucrania
23.42,53.85,p,United Arab Emirates|UAE|Emirados Árabes Unidos|Emiratos Árabes Unidos|Emirados Árabes
55.38,-3.44,p,United Kingdom|UK|Britain|Great Britain|Reino Unido|Grã-Bretanha|Gran Bretaña
52.36,-1.17,p,England|Inglaterra
56.49,-4.2,p,Scotland|Escócia|Escocia
52.13,-3.78,p,Wales|País de Gales|Gales
39.83,-98.58,p,United States|USA|US|America|Estados Unidos|EUA|EE. UU.|EEUU|América
-32.52,-55.77,p,Uruguay|Uruguai
41.38,64.59,p,Uzbekistan|Uzbequistão|Uzbekistán
-15.38,166.96,p,Vanuatu
6.42,-66.59,p,Venezuela
14.06,108.28,p,Vietnam|Vietnã|Vietnam
15.55,48.52,p,Yemen|Iêmen|Yemen
-13.13,27.85,p,Zambia|Zâmbia
-19.02,29.15,p,Zimbabwe|Zimbábue|Zimbabue
-75.25,0.07,r,Antarctica|Antártida|Antártica
32.08,-81.09,c,Savannah
35.23,-80.84,c,Charlotte
39.96,-82.99,c,Columbus
39.77,-86.16,c,Indianapolis
30.33,-81.66,c,Jacksonville
35.15,-90.05,c,Memphis
38.25,-85.76,c,Louisville
43.04,-87.91,c,Milwaukee
44.98,-93.27,c,Minneapolis
38.63,-90.2,c,St. Louis|Saint Louis
39.1,-94.58,c,Kansas City
41.26,-95.94,c,Omaha
35.47,-97.52,c,Oklahoma City
40.76,-111.89,c,Salt Lake City
35.08,-106.65,c,Albuquerque
32.22,-110.97,c,Tucson
38.58,-121.49,c,Sacramento
40.44,-79.99,c,Pittsburgh
41.5,-81.69,c,Cleveland
39.29,-76.61,c,Baltimore
27.95,-82.46,c,Tampa
28.54,-81.38,c,Orlando
36.85,-75.98,c,Virginia Beach
42.89,-78.88,c,Buffalo
47.66,-117.43,c,Spokane
58.3,-134.42,c,Juneau
64.84,-147.72,c,Fairbanks
37.87,-122.27,c,Berkeley
37.44,-122.14,c,Palo Alto
37.39,-122.08,c,Mountain View
37.33,-122.03,c,Cupertino
47.67,-122.12,c,Redmond
30.43,-91.19,c,Baton Rouge
29.42,-98.49,c,San Antonio
31.76,-106.49,c,El Paso
49.9,-97.14,c,Winnipeg
53.55,-113.49,c,Edmonton
46.81,-71.21,c,Quebec City|Cidade de Quebec|Ciudad de Quebec|Québec
44.65,-63.58,c,Halifax
48.43,-123.37,c,Victoria (Canada)
32.53,-117.04,c,Tijuana
20.97,-89.62,c,Mérida (Mexico)|Merida
19.04,-98.2,c,Puebla
16.85,-99.88,c,Acapulco
20.63,-87.08,c,Playa del Carmen
14.08,-87.21,c,Tegucigalpa
13.69,-89.22,c,San Salvador
12.11,-86.24,c,Managua
18.0,-76.79,c,Kingston
18.47,-66.11,c,San Juan
10.65,-61.5,c,Port of Spain|Porto de Espanha|Puerto España
6.8,-58.16,c,Georgetown
5.85,-55.2,c,Paramaribo
10.39,-75.51,c,Cartagena
6.24,-75.58,c,Medellín|Medellin
3.45,-76.53,c,Cali
-2.17,-79.92,c,Guayaquil
-13.53,-71.97,c,Cusco|Cuzco
-17.78,-63.18,c,Santa Cruz de la Sierra
-31.42,-64.18,c,Córdoba (Argentina)
-32.95,-60.64,c,Rosario
-32.89,-68.84,c,Mendoza
-41.13,-71.31,c,Bariloche
-33.05,-71.62,c,Valparaíso|Valparaiso
-23.65,-70.4,c,Antofagasta
-20.32,-40.34,c,Vitória|Vitoria
-27.6,-48.55,c,Florianópolis|Florianopolis
-16.68,-49.25,c,Goiânia|Goiania
-15.6,-56.1,c,Cuiabá|Cuiaba
-20.44,-54.65,c,Campo Grande
-2.53,-44.3,c,São Luís|Sao Luis
-5.79,-35.21,c,Natal
-7.12,-34.86,c,João Pessoa|Joao Pessoa
-9.67,-35.74,c,Maceió|Maceio
-10.91,-37.07,c,Aracaju
-5.09,-42.8,c,Teresina
-8.76,-63.9,c,Porto Velho
-9.97,-67.81,c,Rio Branco
0.03,-51.07,c,Macapá|Macapa
2.82,-60.67,c,Boa Vista
-10.18,-48.33,c,Palmas
-22.91,-47.06,c,Campinas
-23.96,-46.33,c,Santos
-25.52,-54.58,c,Foz do Iguaçu|Foz do Iguacu
-25.69,-54.44,r,Iguazu Falls|Cataratas do Iguaçu|Cataratas del Iguazú
-22.95,-43.21,r,Christ the Redeemer|Cristo Redentor
-3.1,-60.02,r,Amazon River|Rio Amazonas|Río Amazonas
-18.0,-57.0,r,Pantanal
-13.0,-41.4,r,Chapada Diamantina
-3.85,-32.42,r,Fernando de Noronha
57.71,11.97,c,Gothenburg|Gotemburgo|Göteborg
60.39,5.32,c,Bergen
55.6,13.0,c,Malmö|Malmo
56.16,10.21,c,Aarhus
61.5,23.79,c,Tampere
51.92,4.48,c,Rotterdam|Roterdã|Róterdam
52.09,5.12,c,Utrecht
52.08,4.31,c,The Hague|Haia|La Haya
51.22,4.4,c,Antwerp|Antuérpia|Amberes
51.05,3.72,c,Ghent|Gante
50.85,5.69,c,Maastricht
49.61,6.13,c,Luxembourg City|Cidade de Luxemburgo
50.94,6.96,c,Cologne|Colônia|Colonia|Köln
51.23,6.78,c,Düsseldorf|Dusseldorf
48.78,9.18,c,Stuttgart|Estugarda
51.34,12.37,c,Leipzig
51.05,13.74,c,Dresden|Dresde
52.38,9.73,c,Hanover|Hannover|Hanôver
53.08,8.8,c,Bremen
49.45,11.08,c,Nuremberg|Nuremberga|Núremberg|Nürnberg
47.8,13.04,c,Salzburg|Salzburgo
47.27,11.39,c,Innsbruck
47.07,15.44,c,Graz
46.95,7.45,c,Bern|Berna|Berne
47.56,7.59,c,Basel|Basileia|Basilea|Bâle
46.52,6.63,c,Lausanne|Lausana
46.0,7.75,r,Matterhorn|Monte Cervino
45.83,6.86,r,Mont Blanc|Monte Branco|Monte Blanco
43.6,1.44,c,Toulouse
44.84,-0.58,c,Bordeaux|Bordéus|Burdeos
43.7,7.27,c,Nice|Niza
47.22,-1.55,c,Nantes
48.57,7.75,c,Strasbourg|Estrasburgo
50.63,3.06,c,Lille
48.11,-1.68,c,Rennes
43.3,-0.37,c,Pau (France)
49.44,1.1,c,Rouen|Ruão
48.8,2.12,c,Versailles|Versalhes|Versalles
48.64,-1.51,r,Mont Saint-Michel|Monte Saint-Michel
43.55,7.01,c,Cannes
41.38,2.18,r,Sagrada Familia|Sagrada Família
39.47,-0.38,c,Valencia|Valência
36.72,-4.42,c,Málaga|Malaga
37.18,-3.6,c,Granada
41.65,-0.88,c,Zaragoza|Saragoça
43.26,-2.93,c,Bilbao
39.57,2.65,c,Palma de Mallorca|Maiorca|Mallorca
28.12,-15.43,c,Las Palmas
28.47,-16.25,c,Santa Cruz de Tenerife|Tenerife
42.88,-8.54,c,Santiago de Compostela
37.02,-7.93,c,Faro
32.65,-16.91,c,Funchal|Madeira
37.74,-25.67,c,Ponta Delgada|Açores|Azores
40.21,-8.43,c,Coimbra
41.55,-8.42,c,Braga
45.07,7.69,c,Turin|Turim|Turín|Torino
44.41,8.93,c,Genoa|Gênova|Génova|Genova
44.49,11.34,c,Bologna|Bolonha|Bolonia
38.12,13.36,c,Palermo
37.5,15.09,c,Catania|Catânia
43.72,10.4,c,Pisa
43.32,11.33,c,Siena
45.44,10.99,c,Verona
40.63,14.6,r,Amalfi|Costa Amalfitana|Costa Amalfitana
40.55,14.24,r,Capri
37.75,14.99,r,Mount Etna|Etna|Monte Etna
40.82,14.43,r,Mount Vesuvius|Vesúvio|Vesubio
41.89,12.49,r,Colosseum|Coliseu|Coliseo
43.72,10.4,r,Leaning Tower of Pisa|Torre de Pisa
48.86,2.29,r,Eiffel Tower|Torre Eiffel
51.5,-0.12,r,Big Ben
40.69,-74.04,r,Statue of Liberty|Estátua da Liberdade|Estatua de la Libertad
40.75,-73.99,r,Times Square
37.82,-122.48,r,Golden Gate Bridge|Ponte Golden Gate|Puente Golden Gate
27.17,78.04,r,Taj Mahal
40.43,116.57,r,Great Wall of China|Grande Muralha da China|Gran Muralla China|Muralha da China
29.98,31.13,r,Pyramids of Giza|Pirâmides de Gizé|Pirámides de Guiza|Great Pyramid|Grande Pirâmide
13.41,103.87,r,Angkor Wat
30.33,35.44,r,Petra
20.68,-88.57,r,Chichen Itza|Chichén Itzá
25.2,55.27,r,Burj Khalifa
43.08,-79.07,r,Niagara Falls|Cataratas do Niágara|Cataratas del Niágara
44.43,-110.59,r,Yellowstone
36.06,-112.14,r,Grand Canyon Village
-17.92,25.86,r,Victoria Falls|Cataratas Vitória|Cataratas Victoria
-18.29,147.7,r,Great Barrier Reef|Grande Barreira de Coral|Gran Barrera de Coral
35.36,138.73,r,Mount Fuji|Monte Fuji|Fuji
53.48,-2.24,c,Manchester
52.49,-1.9,c,Birmingham
53.8,-1.55,c,Leeds
53.38,-1.47,c,Sheffield
54.98,-1.61,c,Newcastle
55.86,-4.25,c,Glasgow
51.45,-2.59,c,Bristol
51.48,-3.18,c,Cardiff
54.6,-5.93,c,Belfast
51.75,-1.26,c,Oxford
52.2,0.12,c,Cambridge
50.82,-0.14,c,Brighton
53.27,-9.05,c,Galway
51.9,-8.47,c,Cork
50.06,19.94,c,Kraków|Krakow|Cracóvia|Cracovia
51.11,17.04,c,Wrocław|Wroclaw|Breslávia
54.35,18.65,c,Gdańsk|Gdansk
52.41,16.93,c,Poznań|Poznan
49.2,16.61,c,Brno
48.15,17.11,c,Bratislava
46.06,14.51,c,Ljubljana|Liubliana
43.86,18.41,c,Sarajevo
42.44,19.26,c,Podgorica
41.33,19.82,c,Tirana
42.0,21.43,c,Skopje|Escópia
42.65,18.09,c,Dubrovnik
43.51,16.44,c,Split
47.16,27.59,c,Iași|Iasi
45.75,21.23,c,Timișoara|Timisoara
46.77,23.59,c,Cluj-Napoca
47.03,28.86,c,Chișinău|Chisinau|Quichinau
46.48,30.72,c,Odesa|Odessa
49.99,36.23,c,Kharkiv|Carcóvia|Járkov
49.84,24.03,c,Lviv|Lvov
48.0,37.8,c,Donetsk
44.95,34.1,c,Simferopol
44.62,33.52,c,Sevastopol|Sebastopol
45.0,34.0,r,Crimea|Crimeia
55.79,49.12,c,Kazan|Cazã
56.84,60.6,c,Yekaterinburg|Ecaterimburgo
55.03,82.92,c,Novosibirsk
43.12,131.89,c,Vladivostok
54.71,20.51,c,Kaliningrad|Kaliningrado
68.97,33.08,c,Murmansk
62.03,129.73,c,Yakutsk|Iacutsk
40.64,22.94,c,Thessaloniki|Tessalônica|Tesalónica
35.34,25.14,c,Heraklion|Heraklion|Creta
36.39,25.46,r,Santorini
37.45,25.33,r,Mykonos|Míconos
38.42,27.14,c,Izmir|Esmirna
36.9,30.7,c,Antalya
40.18,29.06,c,Bursa
38.64,34.83,r,Cappadocia|Capadócia|Capadocia
41.0,39.72,c,Trabzon
37.07,37.38,c,Gaziantep
36.2,37.13,c,Aleppo|Alepo
35.69,51.42,c,Teheran
32.65,51.67,c,Isfahan|Isfahã|Isfahán
29.61,52.53,c,Shiraz
36.31,59.6,c,Mashhad
31.78,35.23,r,Western Wall|Muro das Lamentações|Muro de las Lamentaciones
32.79,34.99,c,Haifa
31.25,34.79,c,Beersheba|Berseba
31.5,34.47,c,Gaza|Faixa de Gaza|Franja de Gaza|Gaza Strip
31.9,35.2,c,Ramallah
36.19,44.01,c,Erbil
30.51,47.81,c,Basra|Baçorá|Basora
26.22,50.58,c,Manama
17.0,54.0,c,Salalah
12.79,45.04,c,Aden|Adem
24.47,39.61,c,Medina
26.43,50.1,c,Dammam
31.63,65.71,c,Kandahar
39.65,66.96,c,Samarkand|Samarcanda
37.95,58.38,c,Ashgabat|Asgabate|Asjabad
38.56,68.78,c,Dushanbe|Duxambé
42.87,74.59,c,Bishkek|Bisqueque
31.52,74.36,c,Lahore City
33.6,73.05,c,Rawalpindi
34.01,71.58,c,Peshawar
18.52,73.86,c,Pune
23.02,72.57,c,Ahmedabad
26.91,75.79,c,Jaipur
26.85,80.95,c,Lucknow
25.32,82.97,c,Varanasi|Benares
15.5,73.83,r,Goa
9.93,76.27,c,Kochi|Cochim
21.15,79.09,c,Nagpur
22.31,114.17,c,Kowloon
24.48,118.09,c,Xiamen
36.07,120.38,c,Qingdao
38.91,121.6,c,Dalian
45.8,126.53,c,Harbin
41.8,123.43,c,Shenyang
32.06,118.8,c,Nanjing|Nanquim
30.27,120.16,c,Hangzhou
25.04,102.71,c,Kunming
29.65,91.17,c,Lhasa|Lassa
43.83,87.62,c,Ürümqi|Urumqi
39.13,117.2,c,Tianjin
34.75,113.63,c,Zhengzhou
28.23,112.94,c,Changsha
22.82,108.37,c,Nanning
20.04,110.34,c,Haikou
18.25,109.5,c,Sanya
24.15,120.67,c,Taichung
22.63,120.3,c,Kaohsiung
35.87,128.6,c,Daegu
37.46,126.71,c,Incheon
33.5,126.53,r,Jeju|Ilha de Jeju
35.44,139.64,c,Yokohama
35.18,136.91,c,Nagoya
34.69,135.2,c,Kobe
33.59,130.4,c,Fukuoka|Fucuoca
38.27,140.87,c,Sendai
26.21,127.68,c,Naha|Okinawa
34.69,135.8,c,Nara
16.05,108.2,c,Da Nang
16.46,107.59,c,Hue|Huế
20.95,107.08,r,Ha Long Bay|Baía de Ha Long|Bahía de Ha Long
13.36,103.86,c,Siem Reap
17.97,102.6,c,Vientiane|Vienciana
19.89,102.13,c,Luang Prabang
18.79,98.98,c,Chiang Mai
7.88,98.39,c,Phuket
12.93,100.88,c,Pattaya
19.76,96.13,c,Naypyidaw
21.98,96.08,c,Mandalay
5.41,100.33,c,Penang|George Town
1.49,103.74,c,Johor Bahru
4.9,114.94,c,Bandar Seri Begawan
-7.25,112.75,c,Surabaya
-6.92,107.62,c,Bandung
-7.8,110.36,c,Yogyakarta
3.59,98.67,c,Medan
-8.34,115.09,c,Denpasar
10.32,123.89,c,Cebu
7.07,125.61,c,Davao
-9.44,147.18,c,Port Moresby
-18.14,178.44,c,Suva
-12.46,130.84,c,Darwin
-42.88,147.33,c,Hobart
-34.93,138.6,c,Adelaide
-16.92,145.77,c,Cairns
-28.0,153.43,c,Gold Coast
-43.53,172.64,c,Christchurch
-45.03,168.66,c,Queenstown
-21.13,-175.2,c,Nuku'alofa
-13.83,-171.76,c,Apia
-17.53,-149.57,c,Papeete
-22.28,166.46,c,Nouméa|Noumea
21.31,-157.86,r,Pearl Harbor
30.0,31.21,c,Cairo City
25.69,32.64,c,Luxor
24.09,32.9,c,Aswan|Assuã|Asuán
27.26,33.81,c,Hurghada
27.91,34.33,c,Sharm el-Sheikh
34.03,-5.0,c,Fes|Fez|Fès
35.76,-5.83,c,Tangier|Tânger|Tánger
30.42,-9.6,c,Agadir
18.08,-15.98,c,Nouakchott|Nuaquechote
13.51,2.11,c,Niamey
12.13,15.06,c,N'Djamena|Jamena|Yamena
11.59,43.15,c,Djibouti City
3.85,11.5,c,Yaoundé|Yaounde|Iaundé
4.05,9.7,c,Douala
6.37,2.39,c,Cotonou
6.13,1.22,c,Lomé|Lome
5.36,-4.01,c,Abidjan
8.48,-13.23,c,Freetown
6.3,-10.8,c,Monrovia
9.64,-13.58,c,Conakry
11.86,-15.6,c,Bissau
13.45,-16.58,c,Banjul
12.0,8.52,c,Kano
7.38,3.95,c,Ibadan
4.82,7.05,c,Port Harcourt
-1.95,30.06,c,Kigali
-3.38,29.36,c,Bujumbura
-4.27,15.28,c,Brazzaville
0.39,9.45,c,Libreville
3.75,8.78,c,Malabo
0.34,6.73,c,São Tomé|Sao Tome
-4.04,39.67,c,Mombasa
-6.16,39.2,c,Zanzibar
-3.37,36.68,c,Arusha
-13.96,33.79,c,Lilongwe
-15.79,35.01,c,Blantyre
-19.82,34.84,c,Beira
-24.65,25.91,c,Gaborone
-22.56,17.08,c,Windhoek
-29.86,31.03,c,Durban
-33.96,25.6,c,Port Elizabeth|Gqeberha
-29.12,26.21,c,Bloemfontein
-26.33,31.14,c,Mbabane
-29.31,27.48,c,Maseru
-20.16,57.5,c,Port Louis
-4.62,55.45,c,Victoria (Seychelles)
14.93,-23.51,c,Praia
-11.7,43.26,c,Moroni
9.03,38.74,c,Addis
15.33,38.93,c,Asmara
2.05,45.32,c,Mogadiscio
9.56,44.06,c,Hargeisa
4.85,31.58,c,Juba
-0.02,109.34,c,Pontianak
-2.5,-79.0,r,Andes|Cordilheira dos Andes|Cordillera de los Andes
46.5,10.0,r,Alps|Alpes
28.0,84.0,r,Himalayas|Himalaia|Himalaya
46.0,-87.0,r,Great Lakes|Grandes Lagos
53.0,108.0,r,Lake Baikal|Lago Baikal
-16.0,-69.4,r,Lake Titicaca|Lago Titicaca
-1.0,33.0,r,Lake Victoria|Lago Vitória|Lago Victoria
31.5,35.5,r,Dead Sea|Mar Morto|Mar Muerto
43.0,35.0,r,Black Sea|Mar Negro
35.0,18.0,r,Mediterranean|Mediterrâneo|Mediterráneo|Mediterranean Sea
20.0,38.0,r,Red Sea|Mar Vermelho|Mar Rojo
15.0,-75.0,r,Caribbean|Caribe
42.0,51.0,r,Caspian Sea|Mar Cáspio|Mar Caspio
25.0,-90.0,r,Gulf of Mexico|Golfo do México|Golfo de México
27.0,51.0,r,Persian Gulf|Golfo Pérsico
12.0,114.0,r,South China Sea|Mar da China Meridional|Mar de la China Meridional
24.0,120.0,r,Taiwan Strait|Estreito de Taiwan
51.0,1.5,r,English Channel|Canal da Mancha|Canal de la Mancha
36.0,-5.6,r,Strait of Gibraltar|Estreito de Gibraltar|Estrecho de Gibraltar
41.1,29.0,r,Bosphorus|Bósforo
1.3,103.8,r,Strait of Malacca|Estreito de Malaca|Estrecho de Malaca
0.0,-30.0,r,Atlantic Ocean|Oceano Atlântico|Océano Atlántico|Atlantic
0.0,-160.0,r,Pacific Ocean|Oceano Pacífico|Océano Pacífico|Pacific
-20.0,80.0,r,Indian Ocean|Oceano Índico|Océano Índico
80.0,0.0,r,Arctic|Ártico|Arctic Ocean|Oceano Ártico
-60.0,-60.0,r,Drake Passage|Passagem de Drake|Pasaje de Drake
60.0,-150.0,r,Siberia|Sibéria
-35.0,-60.0,r,Patagonia|Patagônia
-25.0,135.0,r,Outback
37.0,127.5,r,Korean Peninsula|Península Coreana
38.3,127.0,r,DMZ|Korean DMZ|Zona Desmilitarizada
24.0,-104.0,r,Sierra Madre
46.0,-122.2,r,Mount St. Helens|Monte Santa Helena
-3.0,-60.0,r,Amazon Basin|Bacia Amazônica|Cuenca del Amazonas
-15.0,-60.0,r,Latin America|América Latina|Latinoamérica
54.0,15.0,r,Europe|Europa
34.0,100.0,r,Asia|Ásia
5.0,20.0,r,Africa|África
29.0,45.0,r,Middle East|Oriente Médio|Oriente Medio
45.0,-100.0,r,North America|América do Norte|América del Norte
-15.0,-60.0,r,South America|América do Sul|América del Sur|Sudamérica
40.706,-74.009,r,Wall Street
-14.27,-170.13,r,Samoa
-17.68,-149.41,r,Tahiti|Taiti|Tahití
13.44,144.79,r,Guam
"""

# nomes que são também palavra comum ou nome de gente: só valem com a palavra "country"/"país" ao lado ou escritos
# como o atlas guarda ("Georgia (country)")
_EXTRAS = """
Germany|Allemagne|Deutschland|Germania
Spain|Espagne|Spanien|Spagna
Italy|Italie|Italien|Italia
France|Frankreich|Francia
United Kingdom|Royaume-Uni|Vereinigtes Königreich|Regno Unito|Großbritannien|Gran Bretagna
United States|États-Unis|Etats-Unis|Vereinigte Staaten|Stati Uniti|USA|U.S.
Brazil|Brésil|Brasilien|Brasile
Mexico|Mexique|Mexiko|Messico
Japan|Japon|Giappone
China|Chine|Cina
Russia|Russie|Russland
India|Inde|Indien
Netherlands|Pays-Bas|Niederlande|Paesi Bassi
Belgium|Belgique|Belgien|Belgio
Switzerland|Suisse|Schweiz|Svizzera
Austria|Autriche|Österreich
Sweden|Suède|Schweden|Svezia
Norway|Norvège|Norwegen|Norvegia
Denmark|Danemark|Dänemark|Danimarca
Finland|Finlande|Finnland|Finlandia
Poland|Pologne|Polen|Polonia
Greece|Grèce|Griechenland|Grecia
Turkey|Turquie|Türkei|Turchia
Egypt|Égypte|Ägypten|Egitto
South Africa|Afrique du Sud|Südafrika|Sudafrica
Australia|Australie|Australien
New Zealand|Nouvelle-Zélande|Neuseeland|Nuova Zelanda
Canada|Kanada
Argentina|Argentine|Argentinien
Chile|Chili|Cile
Peru|Pérou|Perù
Colombia|Colombie|Kolumbien
Venezuela|Vénézuela
Portugal|Portogallo
Ireland|Irlande|Irland
Scotland|Écosse|Schottland|Scozia
England|Angleterre|Inghilterra
Iceland|Islande|Island|Islanda
Ukraine|Ucraina
Israel|Israël|Israele
Saudi Arabia|Arabie saoudite|Saudi-Arabien|Arabia Saudita
Iran|Irán
Iraq|Irak
South Korea|Corée du Sud|Südkorea|Corea del Sud
North Korea|Corée du Nord|Nordkorea|Corea del Nord
Thailand|Thaïlande|Tailandia
Vietnam|Viêt Nam|Viet Nam
Indonesia|Indonésie|Indonesien
Philippines|Philippinen|Filippine
Morocco|Maroc|Marokko|Marocco
Nigeria|Nigéria
Kenya|Kenia
Ethiopia|Éthiopie|Äthiopien|Etiopia
Czech Republic|République tchèque|Tschechien|Repubblica Ceca
Hungary|Hongrie|Ungarn|Ungheria
Romania|Roumanie|Rumänien
Croatia|Croatie|Kroatien|Croazia
Cuba|Kuba
Singapore|Singapour|Singapur
Malaysia|Malaisie|Malaysien|Malesia
Pakistan|Pakistán
Afghanistan|Afghanistan
London|Londres|Londra
Paris|Parigi
Rome|Rom
Munich|München|Monaco di Baviera
Vienna|Vienne|Wien
Brussels|Bruxelles|Brüssel|Bruxelles
Geneva|Genève|Genf|Ginevra
Cologne|Köln|Colonia
Moscow|Moscou|Moskau|Mosca
Warsaw|Varsovie|Warschau|Varsavia
Prague|Prag|Praga
Athens|Athènes|Athen|Atene
Lisbon|Lisbonne|Lissabon|Lisbona
Venice|Venise|Venedig|Venezia
Florence|Florenz|Firenze
Naples|Neapel|Napoli
Milan|Mailand|Milano
Copenhagen|Copenhague|Kopenhagen|Copenaghen
Beijing|Pékin|Peking|Pechino
New York|New York City|Nueva York|Nova Iorque
Mexico City|Mexiko-Stadt|Città del Messico|Mexico
Cairo|Le Caire|Kairo|Il Cairo
Istanbul|Istanbul|Estambul|Istambul
"""

_AMBIGUOS = {"georgia", "jordan", "chad", "turkey", "china", "guinea", "niger", "america", "us", "rio", "la", "porto",
             "salvador", "phoenix", "victoria", "santiago", "georgia country", "jordan country",
             # 2026-11-22: nomes da segunda leva que também são palavra comum, sobrenome ou nome de gente
             "nice", "split", "cork", "medina", "columbus", "mendoza", "santos", "natal", "palmas", "praia", "faro", "hue", "pau", "pisa", "kobe", "darwin", "adelaide", "moroni", "beira", "madeira", "vitoria", "boa vista", "campo grande", "rio branco", "rosario", "granada", "petra", "pacific", "atlantic", "caribbean", "gaza", "aden", "juba", "apia", "georgetown", "kingston", "reading", "mobile", "lagos", "mali", "sendai", "nara"}


def _normal(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _carregar():
    lugares, por_nome = [], {}
    for linha in _ATLAS.strip().splitlines():
        lat, lon, tipo, nomes = linha.split(",", 3)
        nomes = [n.strip() for n in nomes.split("|") if n.strip()]
        lugar = {"lat": float(lat), "lon": float(lon), "tipo": tipo, "nome": nomes[0], "nomes": nomes}
        lugares.append(lugar)
        for n in nomes:
            chave = _normal(re.sub(r"\s*\(.*\)$", "", n))
            # o primeiro que chega fica: as cidades vêm antes dos países, mas "New York" (cidade) vem antes do estado
            por_nome.setdefault(chave, lugar)
    # os nomes em francês, alemão e italiano (2026-11-22): cada linha começa por um nome que o atlas já tem
    for linha in _EXTRAS.strip().splitlines():
        nomes = [n.strip() for n in linha.split("|") if n.strip()]
        lugar = por_nome.get(_normal(nomes[0])) if nomes else None
        if not lugar:
            continue
        for n in nomes[1:]:
            if n not in lugar["nomes"]:
                lugar["nomes"].append(n)
            por_nome.setdefault(_normal(n), lugar)
    return lugares, por_nome


LUGARES, _POR_NOME = _carregar()
_MAIOR_NOME = max(len(k.split()) for k in _POR_NOME)


def achar(nome: str) -> dict | None:
    """O lugar com esse nome (em qualquer das línguas do atlas), ou None."""
    return _POR_NOME.get(_normal(re.sub(r"\s*\(.*\)$", "", str(nome or ""))))


def lugares_no_texto(texto: str) -> list:
    """Os lugares citados no texto, na ordem, sem repetir. Nome ambíguo ("Chad", "Turkey", "China") só conta escrito
    com maiúscula e depois de uma preposição de lugar (in, to, from, em, para, de, en, a, desde, hacia)."""
    palavras = re.findall(r"[\w'’.-]+", str(texto or ""))
    achados, i = [], 0
    while i < len(palavras):
        for tam in range(min(_MAIOR_NOME, len(palavras) - i), 0, -1):
            pedaco = " ".join(palavras[i:i + tam]).strip(".")
            chave = _normal(pedaco)
            lugar = _POR_NOME.get(chave)
            if not lugar:
                continue
            if not pedaco[:1].isupper():
                continue  # "china" (a louça) e "turkey" (o peru) em minúscula não são lugar
            if chave in _AMBIGUOS:
                antes = _normal(palavras[i - 1]) if i else ""
                if antes not in ("in", "to", "from", "em", "no", "na", "para", "de", "do", "da", "en", "a", "desde",
                                 "hacia", "across", "across", "into", "visit", "visited"):
                    continue
            if lugar not in achados:
                achados.append(lugar)
            i += tam - 1
            break
        i += 1
    return achados


def distancia_km(a: dict, b: dict) -> float:
    """A distância em linha reta pela superfície da Terra (fórmula de haversine)."""
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(min(1.0, h)))


def arco(a: dict, b: dict, passos: int = 40) -> list:
    """Pontos (lat, lon) do caminho mais curto entre a e b (o grande círculo), para a rota do mapa."""
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    d = distancia_km(a, b) / 6371.0
    if d < 1e-6:
        return [(a["lat"], a["lon"])]
    saida = []
    for k in range(passos + 1):
        f = k / passos
        x1 = math.sin((1 - f) * d) / math.sin(d)
        x2 = math.sin(f * d) / math.sin(d)
        x = x1 * math.cos(la1) * math.cos(lo1) + x2 * math.cos(la2) * math.cos(lo2)
        y = x1 * math.cos(la1) * math.sin(lo1) + x2 * math.cos(la2) * math.sin(lo2)
        z = x1 * math.sin(la1) + x2 * math.sin(la2)
        saida.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return saida


# contornos simplificados dos continentes (lat, lon), no sentido do contorno: desenho estilizado, não cartografia
CONTINENTES = {
    "america_do_norte": [(71, -156), (70, -141), (69, -120), (72, -95), (66, -85), (63, -93), (58, -94), (55, -82),
                         (60, -78), (62, -74), (58, -68), (60, -64), (52, -56), (47, -53), (44, -66), (41, -70),
                         (35, -76), (30, -81), (25, -80), (30, -84), (29, -90), (29, -95), (26, -97), (21, -97),
                         (18, -94), (21, -87), (16, -88), (15, -83), (11, -84), (8, -77), (9, -80), (7, -82),
                         (13, -88), (14, -92), (16, -95), (19, -105), (23, -110), (31, -114), (24, -110), (28, -115),
                         (34, -120), (38, -123), (43, -124), (48, -125), (55, -131), (59, -139), (60, -147), (57, -157),
                         (60, -165), (66, -168), (71, -156)],
    "groenlandia": [(83, -35), (82, -60), (76, -73), (70, -55), (64, -52), (60, -44), (65, -38), (70, -22), (77, -18),
                    (82, -20), (83, -35)],
    "america_do_sul": [(12, -72), (11, -64), (9, -60), (5, -52), (0, -50), (-2, -44), (-5, -35), (-8, -35), (-13, -38),
                       (-23, -41), (-25, -48), (-29, -49), (-34, -53), (-36, -57), (-39, -62), (-42, -64), (-47, -66),
                       (-52, -68), (-55, -67), (-54, -72), (-50, -75), (-45, -74), (-38, -73), (-30, -71), (-18, -70),
                       (-15, -76), (-6, -81), (-2, -80), (1, -79), (7, -77), (9, -76), (12, -72)],
    "europa": [(36, -9), (43, -9), (44, -1), (48, -5), (49, 0), (51, 2), (53, 5), (55, 8), (57, 8), (56, 11),
               (54, 12), (54, 18), (57, 21), (59, 23), (60, 29), (65, 25), (66, 22), (63, 18), (59, 18), (56, 13),
               (58, 11), (59, 5), (62, 5), (66, 13), (70, 20), (71, 26), (70, 31), (69, 41), (67, 45), (66, 60),
               (55, 60), (47, 49), (42, 48), (41, 41), (41, 29), (40, 26), (37, 24), (39, 20), (42, 19), (45, 13),
               (44, 12), (41, 16), (38, 16), (40, 14), (44, 8), (43, 4), (41, 3), (38, 0), (36, -5), (36, -9)],
    "gra_bretanha": [(50, -5), (51, 1), (53, 0), (55, -2), (58, -2), (58.6, -5), (56, -6), (55, -5), (53, -4),
                     (52, -5), (50, -5)],
    "irlanda": [(51.5, -10), (52, -6), (54, -6), (55.3, -7.5), (54, -10), (51.5, -10)],
    "islandia": [(63.4, -19), (64, -14), (66, -15), (66.5, -22), (65, -24), (63.4, -19)],
    "africa": [(35, -6), (37, 10), (33, 11), (32, 20), (31, 25), (31, 32), (22, 37), (15, 40), (12, 43), (11, 51),
               (2, 46), (-4, 40), (-10, 40), (-15, 41), (-20, 35), (-25, 35), (-30, 31), (-34, 26), (-35, 20),
               (-31, 17), (-22, 14), (-17, 12), (-12, 14), (-6, 12), (-1, 9), (4, 9), (4, 6), (6, 2), (4, -8),
               (8, -13), (11, -15), (15, -17), (21, -17), (24, -16), (28, -13), (31, -10), (35, -6)],
    "madagascar": [(-12, 49), (-16, 50), (-25, 47), (-25, 44), (-21, 43), (-16, 44), (-12, 49)],
    "asia": [(41, 29), (37, 36), (33, 35), (30, 34), (28, 34), (21, 39), (13, 43), (13, 45), (16, 52), (22, 59),
             (26, 56), (24, 52), (30, 48), (27, 56), (25, 62), (25, 67), (21, 72), (16, 73), (8, 77), (13, 80),
             (16, 82), (22, 88), (22, 91), (16, 95), (17, 97), (10, 98), (6, 100), (1, 104), (6, 103), (13, 100),
             (10, 105), (10, 107), (17, 107), (21, 107), (22, 114), (25, 119), (31, 122), (36, 120), (40, 118),
             (40, 122), (39, 125), (35, 126), (35, 129), (39, 128), (43, 131), (48, 140), (54, 141), (59, 143),
             (62, 160), (60, 163), (66, 179), (69, 180), (71, 160), (73, 140), (76, 113), (77, 104), (73, 87),
             (73, 70), (69, 67), (68, 55), (66, 60), (55, 60), (47, 49), (42, 48), (41, 41), (41, 29)],
    "japao": [(31, 130.5), (33.5, 129.8), (35.5, 133), (37, 137), (41.5, 140), (45.5, 142), (43, 145.5), (41, 141.5),
              (38, 141), (35, 140), (34.5, 137), (33.5, 135), (31, 130.5)],
    "taiwan": [(25.3, 121.5), (22, 120.8), (23.5, 120.1), (25.3, 121.5)],
    "sri_lanka": [(9.8, 80), (6, 80), (7, 81.8), (9.8, 80)],
    "sumatra": [(5.6, 95.3), (3, 99), (-2, 104.5), (-5.9, 106), (-3, 101.5), (1, 98.5), (5.6, 95.3)],
    "borneo": [(7, 117), (4, 118.5), (1, 119), (-3.5, 116), (-3, 111), (1.5, 109), (4.5, 114), (7, 117)],
    "java": [(-6, 106), (-6.5, 111), (-7.7, 114.5), (-8.5, 111), (-7.5, 106.5), (-6, 106)],
    "filipinas": [(18.5, 120.8), (14, 120.5), (12, 122), (9.5, 123.5), (6, 125.5), (8, 126.5), (13, 124), (18.5, 120.8)],
    "nova_guine": [(-1, 131), (-2.5, 141), (-6, 147.5), (-10.5, 150), (-8, 143), (-9, 141), (-4, 135), (-1, 131)],
    "australia": [(-11, 142), (-16, 145), (-19, 147), (-25, 153), (-29, 153.5), (-33, 152), (-37.5, 150),
                  (-39, 146), (-38, 141), (-35, 138), (-35, 136), (-32, 133), (-34, 124), (-35, 118), (-34, 115),
                  (-31, 115), (-26, 113), (-22, 114), (-20, 119), (-17, 123), (-14, 127), (-15, 129), (-12, 131),
                  (-12, 136), (-15, 135.5), (-17.5, 140), (-11, 142)],
    "nova_zelandia_norte": [(-34.5, 172.7), (-37, 175.5), (-37.7, 178.5), (-41.5, 175.3), (-39.5, 174), (-34.5, 172.7)],
    "nova_zelandia_sul": [(-40.5, 172.7), (-42, 174), (-44, 173), (-46.5, 169.5), (-46, 166.5), (-43.5, 170), (-40.5, 172.7)],
    "cuba": [(23, -84.5), (23.2, -80), (21.5, -76), (20, -74.2), (20, -77.5), (21.8, -81), (22, -84.8), (23, -84.5)],
    "hispaniola": [(19.9, -72.8), (19.8, -70), (18.5, -68.4), (18, -71.5), (18.3, -74.4), (19.9, -72.8)],
}
