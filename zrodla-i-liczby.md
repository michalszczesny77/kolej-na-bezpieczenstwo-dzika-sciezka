# Źródła i liczby

Dokument referencyjny do prezentacji "Dzika Ścieżka" (konkurs PKP PLK "Kolej na bezpieczeństwo", II edycja, wyzwanie nr 2). Stan na 20.11.2026, dotyczy ostatecznej wersji prezentacji z 19 slajdami (`prezentacja/Dzika_Sciezka.pdf`; slajd 18 odsyła do tego pliku).
Repozytorium (publiczne): https://github.com/michalszczesny77/kolej-na-bezpieczenstwo-dzika-sciezka
Każda liczba ze slajdów (tekst, wykresy, zrzuty demo) ma tu źródło i sposób policzenia, w kolejności slajdów. Pełne ponowne sprawdzenie wykonano 19.11.2026: liczby z danych własnych przeliczono na plikach z folderu `dane/`, liczby z dokumentów sprawdzono w źródłach pierwotnych (otwarte pliki PDF, XLSX, XLSM i teksty ustaw; podane strony i arkusze).
Numery slajdów = numery stron PDF (1-19). Ścieżki są względne wobec korzenia repozytorium (`dane/`, `kod/`, `demo/`). Numery stron dokumentów to numery stron pliku PDF. Adresy źródeł: sekcja 4. Opis każdego pliku z `dane/`: `dane/README.md`.

## 1. Liczby w prezentacji

Skróty: SBR = UTK, Sprawozdanie ze stanu bezpieczeństwa ruchu kolejowego 2025; `ranking.csv` = `dane/ranking.csv` (82 kandydatów, 63 miejsca).

### Slajd 1 - tytuł

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Wyzwanie nr 2 "Czy AI może przewidzieć zagrożenie?" | nr 2 | Regulamin konkursu § 4 ust. 2 pkt 2 | cytat tytułu |
| Zdjęcie: miejsce nr 1 | ul. Manganowa, T1-0060 | `ranking.csv`, wiersz rank = 1; ortofotomapa GUGiK, zdjęcie z 03.06.2023 (`dane/t1b/ortho_dates.json`, komórka 360_361) | kółko = lat 51,10336, lon 17,00229; to samo ujęcie co na slajdzie 7 |
| "Najtańszy skuteczny środek" | dobór wg reguł (sekcja 3, "Dobór środka") | `dane/interventions.json` (15 środków), `ranking.csv` (`rule`, `intervention_primary`) | "najtańszy" = z katalogu o najniższym koszcie spełniający reguły; skuteczność środków nie jest zmierzona dla naszych miejsc |
| Autorzy | dwie osoby | dane na slajdach 1 i 19 | tu bez danych osobowych |

### Slajd 2 - problem

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| 121 osób nieupoważnionych w 2025 | 121 | SBR, Tab. 9, s. 23 (wiersz 4 "nieupoważniony") | odczyt z tabeli |
| 68,4% wszystkich zabitych | 68,4% (121 ze 177) | SBR s. 25 ("68,4% ogółu ofiar śmiertelnych"); Tab. 9 (razem 2025 = 177) | 121/177 = 0,6836; dotyczy wypadków na liniach kolejowych (bez bocznic) |
| "Co 3 dni" (tytuł) | 3,02 dnia | wyliczenie | 365 / 121 |
| Wykres 2021-2025 | 100, 121, 115, 119, 121 | SBR, Tab. 9, s. 23 | odczyt z tabeli |
| "Od 2022 r. bez trwałego spadku" | min 115 (2023), maks 121 (2022, 2025) | SBR, Tab. 9 | min/maks z lat 2022-2025 |
| Stopka: s. 56 | kategoria 34 (przechodzenie przez tory poza przejściami) "najczęściej w obrębie dzikich przejść" | SBR s. 56 | cytat; tabela 9 liczy wszystkich nieupoważnionych zabitych w wypadkach, nie tylko na dzikich przejściach (kat. 34 w 2025: 122 zabitych, s. 56) |

### Slajd 3 - skala problemu

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Zabici nieupoważnieni w 2025 | 121 | SBR, Tab. 9, s. 23 | odczyt z tabeli (zob. slajd 2) |
| Koszt jednej ofiary | 4,3 mln zł (4 316 219,48 zł) | CUPT, koszty jednostkowe ver. 2026-05-28, arkusz "Wypadki", komórka Z41 (kolumna 2026, poziom cen 31.12.2025) | odczyt; tytuł tabeli: "Koszty jednostkowe wypadków drogowych"; CUPT nie podaje stawki dla wypadków kolejowych (wytyczne CUPT dla kolei z 2023 odsyłają do kosztów drogowych), co slajd zaznacza |
| 522 mln zł | ok. 522 mln zł (522 262 557 zł) | j.w. | 121 x 4 316 219,48; skala problemu w kraju, nie efekt projektu |
| "Co 3 dni" | 3,02 dnia | wyliczenie | 365 / 121 |
| 68,4% wszystkich zabitych | 68,4% (121 ze 177) | SBR s. 25; Tab. 9 (razem 2025 = 177) | zob. slajd 2 |
| Najwięcej w UE: 116 z 492 (2024) | 116 z 492 (23,6%); Niemcy 96, Rumunia 54, Włochy 49, Francja 39 | Eurostat, Rail accidents and fatalities (12.2025), arkusz "Table 1", kolumna "Unauthorised persons", wiersze EU i Poland | 116/492 = 0,236; Polska ma najwyższą liczbę wśród państw UE |

### Slajd 4 - dlaczego przechodzą

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Skrót "kilkadziesiąt metrów, mniej niż minuta" | 60 m (wartość modelowa) = ok. 43 s | `ranking.csv`, `detour_straight_m` (mediana 60; 70 z 82 punktów dokładnie 60); `kod/t3_exposure/detour.py` (OFFSET_M = 30) | odległość między punktami 30 m od osi toru po obu stronach, nie pomiar ścieżki; 60 m przy 5 km/h = 43 s |
| Legalna droga "często ponad kilometr, kwadrans i więcej" | mediana 1 198 m (ok. 14 min); 52 z 82 punktów powyżej 1 km; 22 powyżej 2 km; 10 powyżej 3 km; maks. 5 829 m | `ranking.csv`, `detour_walk_m` | trasa pieszo po grafie OSM do najbliższego legalnego przejścia; 1 km przy 5 km/h = 12 min |
| "Między legalnymi przejściami po kilka kilometrów" | najdłuższe trasy do legalnego przejścia: 5,8 km | `ranking.csv`, `detour_walk_m` | to długość trasy z danego miejsca, nie rozstaw przejść; UTK (s. 60) wskazuje ryzyko "długich odcinków linii w okolicach skupisk ludzkich bez bezpiecznego przejścia" |
| "Tory dzielą osiedla", "Wydeptana ścieżka zaprasza" | opis | SBR s. 56 i s. 60 (jednostronne dojścia do peronów, brak przejść przy zabudowie); `ranking.csv` (`dest_list_a`, `dest_list_b`) | opis; ostatnia karta ("raz przetarty skrót staje się zwykłą drogą") to ocena autorów, bez liczby |

### Slajd 5 - cel

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| "Nie znaleźliśmy jednej, jawnej mapy" | brak jawnego rejestru krajowego | przegląd przepisów i dokumentów publicznych; PLK Id-1 Moduł D2, Zał. 1 (D2AD), arkusze "Kody", "Listy", "AD - pkt 2 wg wskazań IK", kod OTDZ "Otoczenie terenu - dzikie przejścia" | kod OTDZ odczytany w pliku D2AD; brak oficjalnego potwierdzenia PLK |
| NIK: wykazy ZLK i SOK się nie zgadzały | 51 wobec 43 | NIK P/16/029, s. 35: "w ZLK Siedlce na obszarze podległym KR SOK w Lublinie, SOK zidentyfikowała 51 dzikich przejść (w wykazie Zakładu było ich 43)" | odczyt; w tym samym miejscu 7 wobec 70 (wykaz warszawski z 2014 r.) i 12 nowych miejsc stwierdzonych przez NIK |
| "W kontroli NIK (lata 2015-2016)" | kontrola obejmuje 2015-2016 (I półrocze) | NIK P/16/029, s. 8 ("Kontrolą objęto okres 2015-2016 (I półrocze)") | odczyt; wykaz z 2014 r. (7 wobec 70, s. 35) dotyczy ZLK dla KR SOK Warszawa i nie występuje na slajdzie; raport z marca 2017 (stopka slajdu: 2017) |
| Standardy Techniczne Tom XIV, zał. 1: model decyzyjny wygrodzeń wymaga liczby dzikich przejść na km | kryterium 3: "Występowanie dzikich przejść w przeliczeniu na jeden kilometr linii", waga 3, oceny 0 / 2 / 4 / 6 (brak; poniżej 1/km; 1 do poniżej 3/km; 3 lub więcej/km) | PLK, Standardy Techniczne Tom XIV (WCAG, 11.04.2022), Załącznik nr 1 "Model decyzyjny dokonywania oceny zasadności budowy wygrodzeń linii kolejowych", s. 18; pkt 3.1: decyzja o ogrodzeniu "po dokonaniu analizy według Załącznika nr 1" | odczyt; załącznik każe "przygotować dane" do kryteriów, nie wskazuje źródła liczby dzikich przejść |
| "Nasza lista tę liczbę dostarcza" | lista kandydatów z OSM + wykryć AI dla aglomeracji Wrocławia | `ranking.csv`, `dane/candidates_ai.geojson` | to lista wyszukana, nie pełny wykaz; liczba na km wymaga potwierdzenia w terenie |
| Stopka: Id-1 Moduł D2, zał. 1 (kod OTDZ) | kod OTDZ | Id-1 D2AD | zob. wyżej |

### Slajd 6 - trzy kroki

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| 3 kroki: wykryj, oceń, dobierz | model wizyjny, model ryzyka, katalog środków | `kod/t1b_ortho_ai/`, `kod/t6_scoring/score.py`, `dane/interventions.json` (15 środków) | opis metody |
| "Jawny model ... w jeden wynik 0-100" | wynik 0-100 | `ranking.csv`, kolumna `score` | wzór: sekcja 3 |
| "Najtańszy środek, który rozwiązuje jego problem" | reguły doboru | `ranking.csv` (`rule`) | zob. slajd 10 |
| Nadzór: zatwierdza pracownik PLK | proponowany proces docelowy | decyzja autorów | PLK nie wdrożyła takiego systemu (sekcja 2) |
| "Docelowo uzupełniają je wykazy zakładów linii i SOK" | propozycja | autorzy | brak liczb; PLK nie została poproszona o dane (praca wyłącznie na danych publicznych) |

### Slajd 7 - krok 1: wykryj

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Zdjęcia 100 x 100 m | kadr 100 x 100 m | `kod/t1b_ortho_ai/crops.py` (CROP_HALF_M = 50), `finalize.py` | wycinek ortofotomapy GUGiK wokół punktu na torze |
| "Wzdłuż linii" | 4 480 punktów co 60 m wzdłuż linii w ramce Wrocławia (lat 50,95-51,30; lon 16,75-17,35); do skanu 3 143 kadry (ludność w 500 m >= 50) | `kod/t1b_ortho_ai/build_index.py` (SPACING_M = 60), `common.py` (BBOX), `fetch_tiles.py` (POP_MIN = 50); `dane/t1b/scan_all_index.json`, `scan_index.json`; `cv_report_round1.json` (scan.n_tiles = 3 143) | zliczenie; to linie w aglomeracji Wrocławia, nie cała sieć kraju |
| Człowiek potwierdza | proponowany proces | decyzja autorów | brak liczb |
| Definicja: ścieżka lub droga przez tory poza legalnym przejściem; przepusty, rurociągi i tory stacyjne odrzucane | definicja robocza zespołu | spójna z kategorią UTK nr 34 (SBR s. 56), która klasyfikuje wypadki, nasza definicja dotyczy obiektu | w uczeniu jako trudne negatywy użyto peronów (144) i przejść dwupoziomowych (120) oraz 27 fałszywych wskazań z rundy 1 (`dane/t1b/hard_negatives_index.json`); przepusty i rurociągi nie są osobną klasą |
| Zdjęcie "Tak: ścieżka widoczna po obu stronach toru" | to samo ujęcie co slajd 1 (Manganowa) | `ranking.csv` T1-0060; ortofotomapa GUGiK | ilustracja |

### Slajd 8 - nadzór człowieka

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Dokument | PLK Id-1 (uchwała 1037/2025), Moduł D2 "Diagnostyka - dozorowanie" | pakiet Id-1 (sekcja 4), plik "Id-1_Moduł D2 - Diagnostyka - dozorowanie.pdf" | otwarty plik |
| "Obowiązek sprawdzać, czy nie powstały nowe dzikie przejścia" | § 15 ust. 8 pkt 1 lit. d, s. 18 | Id-1 D2 | cytat: "nie powstały dzikie przejścia" |
| "Pracownik PLK sprawdza miejsce w czasie obchodu toru" | obchód; obchód specjalny na zgłoszenie: § 9 ust. 1 pkt 2 lit. c, s. 10 | Id-1 D2 | cytat: "otrzymane zgłoszenia o wadach w infrastrukturze"; forma zgłoszeń dowolna; uznanie wykrycia AI za takie zgłoszenie to interpretacja zespołu |
| "Wpisuje do arkusza dozorowania" | Arkusz Dozorowania, kod wady OTDZ | Id-1 D2, Zał. 1 (D2AD), arkusze "Kody", "Listy", "AD - pkt 2 wg wskazań IK" | odczyt |
| "Co roku: nowe zdjęcia, rozkład jazdy i mapa uruchamiają kolejną rundę" | propozycja | autorzy | zob. sekcja 2 |
| 4 kroki: zgłoszenie, teren, decyzja, co roku | proponowany proces docelowy | decyzja autorów | PLK nie wdrożyła takiego systemu |

### Slajd 9 - krok 2: oceń

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Wzór | Wynik = 100 x pierwiastek 3. stopnia z (E x D x H), czynniki 0-1 | `kod/t6_scoring/score.py` | uzasadnienie: sekcja 3 |
| A, Manganowa: wynik | 78/100 (78,1) | `ranking.csv` T1-0060: score 78,1 | 100 x (1,000 x 0,826 x 0,576)^(1/3) = 78,1 |
| A: E, D, H | 1,00; 0,83; 0,58 | `ranking.csv`: E 1,000 (nasycone), D 0,826, H 0,576 | E = min(1, 47 217 / 30 091)^0,5; D = (1 256,4 - 100) / 1 400; H = 0,4 x 0,375 + 0,4 x 0,731 + 0,2 x 0,667 |
| A: mieszkańcy | 7 262 w 500 m | `ranking.csv`, `pop_500m` = 7 262,3 | 1 821,8 + 5 440,5 (obie strony toru), siatka GUS NSP 2021 |
| A: legalna droga | 1,3 km (1 316,4 m) | `ranking.csv`, `detour_walk_m` | trasa pieszo po grafie OSM do najbliższego legalnego przejścia |
| A: "ruch umiarkowany" | 78 pociągów pasażerskich na dobę, 60 km/h, 2 tory | `ranking.csv`: `trains_per_day`, `vmax_kmh`, `tracks_crossed` | określenie opisowe (H = 0,58); linia 761, Regulamin sieci zał. 2.1; GTFS PolishTrains, oba kierunki |
| B, Słupska: wynik | 53/100 (53,1) | `ranking.csv` T1-0042: score 53,1 (miejsce 13 z 63) | 100 x (0,658 x 0,267 x 0,854)^(1/3) = 53,1 |
| B: E, D, H | 0,66; 0,27; 0,85 | `ranking.csv`: E 0,658, D 0,267, H 0,854 | E = (13 021 / 30 091)^0,5; D = (473,8 - 100) / 1 400; H = 0,4 x 1,0 + 0,4 x 0,802 + 0,2 x 0,667 |
| B: legalna droga | 0,5 km (533,8 m) | `ranking.csv`, `detour_walk_m` | nadkład względem skrótu 473,8 m (też ok. 0,5 km) |
| B: prędkość, pociągi | do 160 km/h; 94 na dobę | `ranking.csv`: `vmax_kmh` = 160, `trains_per_day` = 94 (linia 275) | Regulamin sieci zał. 2.1; GTFS PolishTrains, pociągi pasażerskie, oba kierunki |
| "Wagi i progi to jawne założenia" | wagi H 0,4 / 0,4 / 0,2, progi p95 | sekcje 2 i 3 | założenia autorów |

### Slajd 10 - krok 3: dobierz

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Reguły doboru (legalna droga blisko, daleki objazd, wiele torów lub szybki ruch, peron, od zaraz) | ogrodzenie przy legalnej drodze do 300 m; przejście kat. E do 3 torów i 160 km/h; kładka lub tunel powyżej; nowe dojście do peronu; patrol SOK, tablice ostrzegawcze i edukacja zawsze | `kod/t6_scoring/score.py`, `ranking.csv` (`rule`, `intervention_primary`); Dz.U. 2025 poz. 1105, § 5 (nie więcej niż 160 km/h) i § 11 ust. 2 (więcej niż trzy tory: systemy przejazdowe); próg 300 m: Silla i Luoma (2011) | sekcja 3 "Dobór środka"; kat. E = § 11 ust. 1 ("Do kategorii E zalicza się przejścia przez tory kolejowe") |
| W top-20: struktura środków | 12 przejść kat. E, 6 kładek, 2 dojścia do peronu | `ranking.csv`, `intervention_primary` (miejsca 1-20) | zliczenie: I5 = 12, I6 = 6, I13 = 2 (dane do slajdu 15, nie wyświetlane na slajdzie 10) |
| Stopka: "sam płot przesuwa problem na sąsiedni odcinek" | obserwacja z literatury | FDOT-CFRC Trespass Report (01.2020): "Moving the trespassing to a new location does not reduce the safety risk"; RSSB: "trespassers go to other unprotected sections" | źródła mówią o przesunięciu ruchu na inne miejsce lub odcinek; slajd nie podaje odległości |

### Slajd 11 - oczekiwana zmiana

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| "Mniej interwencji wobec osób na torach" (SOK) | oczekiwanie, bez liczby | SBR s. 60 (akcja SOK "Dzikie Przejścia" w 2025: działania na 57 385 przejściach, 4 726 mandatów, wg Komendy Głównej SOK) | oczekiwana zmiana jest założeniem autorów; liczby SOK nie ma na slajdzie |
| "Przerwanie serii 115-121 zabitych osób nieupoważnionych rocznie, która trwa od 2022 r." | 115-121 rocznie | SBR, Tab. 9, s. 23 | min/maks z lat 2022-2025; to wszyscy zabici nieupoważnieni, nie tylko na dzikich przejściach (zob. slajd 2) |
| "Dziś Polska ma najwięcej takich ofiar w Unii: 116 z 492 (2024)" | 116 z 492 | Eurostat, arkusz "Table 1" | zob. slajd 3; Eurostat podaje 116 dla 2024, UTK w Tab. 9 podaje 119 (inna definicja zdarzeń; Raport UTK za 2025, wskaźniki CSI, podaje 116 dla 2024 i 118 dla 2025) |
| "Seria CSI" (stopka) | Eurostat, tran_sf_railvi | Eurostat, arkusz "Table 1": źródło "online data code: tran_sf_railvi" | nazwa "CSI" za Raportem UTK (dane wg wytycznych ERA); w pliku Eurostatu hasła CSI nie ma |
| Miary sukcesu | interwencje SOK, zabici w danych UTK, pozycja w Eurostacie | propozycja autorów | brak celów liczbowych (sekcja 2) |

### Slajd 12 - wdrożenie w PKP PLK

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| "Mamy dziś: zdjęcia lotnicze, mapa torów i przejść, ludzie i cele, ruch pasażerski" | otwarte dane krajowe | ortofotomapa GUGiK (WMS), OSM, GUS NSP 2021 (siatka 250 m), GTFS PolishTrains, Regulamin sieci | zob. slajd 18 |
| "PLK dokłada: współrzędne wypadków, wykazy ZLK i SOK, ruch towarowy, aktualna mapa i obchody" | propozycje | autorzy | brak liczb; UTK podaje tylko sumy krajowe (SBR), wykazy i ruch towarowy nie są publiczne |
| "Co to naprawia: ranking sprawdzony na pełnych danych" | walidacja na 23 zdarzeniach z prasy lokalnej (wynik zanonimizowany) | `dane/t6_validation.json`, `dane/t6_validation_events.csv` (23 wiersze) | zob. sekcja 3, "Walidacja" |
| "Nowy obszar to tylko zmiana parametru" | założenie | ramka obszaru zapisana w skryptach (`kod/t1b_ortho_ai/common.py`, BBOX) | nie testowano poza aglomeracją Wrocławia |

### Slajd 13 - odpowiedzialne użycie AI

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| "Z prasy bierzemy tylko rok i miejsce zdarzenia" | zasada projektu | `README.md` (sekcja Prywatność); `dane/validation.geojson`, `dane/t6_validation_events.csv` (kolumny: id, rok, dokładność, promień, kandydaci) | opis zdarzeń przechowują lokalnie autorzy; w repozytorium tylko wynik zanonimizowany (rok, skutek, współrzędne zaokrąglone do ok. 100 m) |
| "Zero danych osobowych w procesie analizy" | zasada projektu | j.w. | w analizie i w demo nie ma danych osób; źródła prasowe przechowywane lokalnie dotyczą konkretnych zdarzeń |
| "AI tylko przesiewa; wpis zatwierdza pracownik PLK po wizji" | proponowany proces | decyzja autorów | model: DINOv2 ViT-S/14 + regresja logistyczna, 3 143 kadry skanu zawężone do 40 wskazań do oglądu (sekcja 3) |
| "Model wskazuje miejsca, nie przewiduje wypadków" | brak istotnej zależności od potrąceń (p > 0,1, n = 23) | `dane/t1b/cv_report_round1.json`, `cv_report_round2.json`; `kod/t1b_ortho_ai/eval_events.py` na `dane/t1b/validation_events.json` | wynik poza prezentacją (sekcja 3) |
| "Samobójstwa są poza zakresem" | kategoria osobna: 156 w 2025 | SBR s. 56, Tab. 14 | odczyt |
| "Każdy wynik da się przeliczyć i podważyć" | jawny wzór | `kod/t6_scoring/score.py`, `ranking.csv` | sekcja 3 |

### Slajd 14 - case study: Wrocław

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| 82 kandydatów na dzikie przejścia | 82 | `ranking.csv` (82 wiersze) | zliczenie; wszyscy mają źródła z OSM: deadend_stubs 33, shared_node 22, informal_tag 14, hazard_tag;shared_node 8, shared_node;informal_tag 5; wykrycia AI są osobnym przesiewem, poza rankingiem |
| 63 miejsca w rankingu | 63 | `ranking.csv` (63 wiersze `place_leader`) | miejsce = kandydaci w promieniu 300 m (zachłannie, wiodący = najwyższy wynik) |
| 20 najgroźniejszych z kartą i zaleceniem | 20 | `dane/top20/` (20 plików .md i 20 .jpg, plus `index.md`); `ranking.csv` | top-20 miejsc obejmuje 31 punktów |
| Zasięg "aglomeracja Wrocławia" | lat 50,969-51,275; lon 16,847-17,267 | `ranking.csv` | 7 z 82 punktów leży > 15 km od centrum (maks. 20,5 km) |
| Zrzut mapy z demo: lista | Manganowa 78,1; Stalowa 71,3; Wilhelma Grapowa 66,8; Bolesława Krzywoustego 62,3; Bystrzycka 62,3; Karpnicka 61,6; Kleczkowska 60,9; Kwiatowa 60,7; Żernicka 55,9; Franza Petera Schuberta 55,5; Górecka 53,7; Królewiecka 53,4; Słupska 53,1 | `ranking.csv` (`score`, `place_rank`) | odczyt; nazwa = najbliższa ulica z OSM; numery linii z `lines_30m`; środek z `intervention_primary` |
| Zrzut: zakładki i legenda | Ranking 63, Wykrycia AI 12, Wpisy 0; "Wyświetlono 20 z 63 miejsc"; legenda wyniku: < 25, 25-40, 40-50, 50-60, 60+ | `demo/Dzika_Sciezka_demo.html` (dane w `DATA`) | liczniki z danych dema; znaczniki numerowane = top-20, kwadraty = wykrycia AI |
| "Dane wejściowe są krajowe, ten sam proces działa dla każdego zakładu linii" | założenie | zob. slajd 12 | nie testowano poza Wrocławiem |

### Slajd 15 - demo: karta miejsca

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| 78,1 / 100, miejsce nr 1 z 63 | 78,1; 1 z 63 | `ranking.csv` T1-0060 | zob. slajd 9 |
| Powód: ekspozycja 1,00, objazd 0,83, zagrożenie 0,58 | 1,00; 0,83; 0,58 | `ranking.csv` | zob. slajd 9 |
| Karta: linia 761, km 0,4, stacja Wrocław Mikołajów (1,5 km) | 761; 0,4; 1,5 km | `ranking.csv` (`line_nearest`, `station`, `station_m` = 1 464); `dane/rail_hazard.geojson` (km 0,24-0,49) | odczyt |
| Karta: "Zdarzenia w 300 m: 0", "Brak wpisów w rejestrze" | 0; brak | `dane/t6_validation_events.csv`; stan demo | brak zdarzenia z prasy w pobliżu |
| Karta: 7 262 mieszkańców w 500 m; legalnie 1,3 km zamiast 60 m | 7 262; 1,3 km; 60 m | `ranking.csv` | zob. slajdy 4 i 9 |
| "Legalne przejście kat. E z labiryntem/barierkami" | 14 000-1 500 000 zł/przejście | `dane/interventions.json`, I5 | Legionowo (Piaski, 2012: ok. 14 tys. zł) i Warszawa Wileńska (Rynek Kolejowy 1.02.2025: 1,5 mln zł netto) jako krańce zakresu; ceny nominalne |
| Od zaraz: patrol SOK 18-23 + pomiar ruchu przed/po | okno 18-23 | SBR s. 58 | w tych godzinach 39,4% wypadków kat. 34 z lat 2021-2025 (cytat: godz. 18-23, "jedna czwarta doby") |
| Wsparcie: ogrodzenie standardowe | 26 000-134 000 zł | `interventions.json`, I1: 130-670 zł/mb | założenie 2 x 100 m ogrodzenia kanalizującego (Clapperton: min. 100 m); 200 m x 130 = 26 000, 200 m x 670 = 134 000 |
| Zawsze: tablice z informacją o mandacie (2 szt.) | 600-4 000 zł | `interventions.json`, I9: 300-2 000 zł/szt. | 2 szt.; cennik budżetu obywatelskiego (Koszalin), założenie |
| Zalecenie na slajdzie: "legalne przejście, a od zaraz patrol SOK i tablice" | I5 + etap 0 | `ranking.csv` T1-0060 (`intervention_primary` = I5_przejscie_kat_E); karta `dane/top20/01_T1-0060.md` | zob. slajd 10 |
| Lista po lewej (top-13) | zob. slajd 14 | `ranking.csv` | zob. slajd 14 |

### Slajd 16 - demo: weryfikacja wykryć AI

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| 12 wykryć AI czeka na sprawdzenie | 12 | `dane/candidates_ai.geojson` (12 obiektów) | zliczenie; w naszym przeglądzie zdjęć 2 uznano za potwierdzone (AI-001, AI-002), 10 za niepewne; w terenie nic nie sprawdzano |
| AI-001: pewność modelu | 1,00 (0,9999) | `candidates_ai.geojson`, `ai_score` | zaokrąglenie |
| AI-001: zdjęcie lotnicze | 03.06.2023 | `candidates_ai.geojson`, `ortho_date` | odczyt |
| AI-001: oficjalne przejście | 53 m | `candidates_ai.geojson`, `nearest_official_m` = 52,7 | odległość do najbliższego legalnego przejścia z OSM |
| AI-001: współrzędne | 51,15047; 17,02821 | `candidates_ai.geojson` | odczyt |
| AI-001: linia, kilometr | 292, km 22,0-27,1 | `candidates_ai.geojson` (`rail_line_no`); `dane/rail_hazard.geojson`, linia 292, `km_from` 22,026, `km_to` 27,063 | odcinek OSM o długości 5,2 km; dokładny kilometr ze słupka nieznany |
| AI-001: ruch, prędkość, tory (poza zrzutem) | 0 pociągów pasażerskich; 40 km/h; 1 tor | `rail_hazard.geojson`, ten sam odcinek | Regulamin sieci zał. 2.1 i GTFS; ruch towarowy nieznany |
| Obchód specjalny | Moduł D2 § 9 ust. 1 pkt 2 lit. c | Id-1 D2, s. 10 | zob. slajd 8 |
| Stopień wadliwości "U3 - stan dopuszczalny" | U3 | Id-1 Moduł D3, tabela 1 (stopnie U1-U4; U3 = "dopuszczalny"); Moduł D2 odsyła do D3 | odczyt; wybór U3 na zrzucie jest przykładowy |
| OTDZ "Otoczenie terenu - dzikie przejścia" | kod wady | Id-1 D2, Zał. 1 (D2AD), arkusze "Kody", "Listy" | odczyt; "Docelowo potwierdzone trafia do arkusza" to propozycja procesu |
| Trzy decyzje: potwierdź, skoryguj, usuń | proponowany proces | decyzja autorów | brak liczb |
| Pola formularza (nr AD, data 18.11.2026, wpisy Z-0001) | dane przykładowe | demo | wymyślone do zrzutu, tylko w przeglądarce |

### Slajd 17 - pilotaż: krok zero

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| "Top 20 dla Wrocławia już jest: karta miejsca, wynik i zalecany środek" | 20 miejsc z kartą | `dane/top20/` (20 kart), `ranking.csv` (miejsca 1-20) | zliczenie; zob. slajdy 14-15 |
| Weryfikacja w czasie obchodów, które pracownicy już wykonują | proponowany proces | Id-1 Moduł D2 § 15 ust. 8 | zob. slajd 8 |
| Od zaraz: patrol SOK, tablice i akcje edukacyjne w szkołach w promieniu 500 m od miejsc z top 20 | propozycja | decyzja autorów; promień 500 m jak w ekspozycji E (sekcja 3); szkoły to jeden z rodzajów celów w E (OSM) | brak liczb; liczby szkół na slajdzie nie podajemy |
| Pomiar: interwencje SOK przed i po; kolejne zakłady to zmiana parametru | proponowana miara | zob. slajd 11; ramka obszaru w `kod/t1b_ortho_ai/common.py` (BBOX) | brak liczb; poza aglomeracją Wrocławia nie testowano |
| "Start bez budowy: dane otwarte, istniejące obchody i patrole SOK" | propozycja | slajdy 8, 12 | brak liczb |

### Slajd 18 - dane, źródła i licencje

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| OpenStreetMap (ekstrakt Geofabrik) · ODbL 1.0 | pobrania 13-14.11.2026 | `dane/README.md` (sekcja "Surowe dane"); Geofabrik `dolnoslaskie-261113.osm.pbf` (13.11), Overpass (14.11) | atrybucja "(c) autorzy OpenStreetMap" |
| Ortofotomapa GUGiK · bez opłat, art. 40a Pgik | art. 40a ust. 2 pkt 1 lit. e | Prawo geodezyjne i kartograficzne, tekst jednolity Dz.U. 2026 poz. 1389: "Nie pobiera się opłaty za: 1) udostępnianie zbiorów danych: ... e) ortofotomapy" | otwarty tekst ustawy; zdjęcia z lat 2019-2025 (`dane/t1b/ortho_dates.json`) |
| GUS, NSP 2021 · z podaniem źródła | siatka 250 m | `dane/README.md` (`NSP2021_TOT_GRID250m_GPKG.zip`) | brak oficjalnej strony z licencją dla tego zasobu |
| Regulamin sieci PLK; GTFS; BIP; CC0/MIT | warunki ponownego wykorzystania: źródło, czas wytworzenia i pozyskania, poinformowanie PLK; PolishTrainsGTFS: geometrie CC0 1.0, kod MIT | https://bip.plk-sa.pl/ponowne-wykorzystywanie; README PolishTrainsGTFS | zawiadomienia do PLK nie składano; praca trafia do PLK jako organizatora konkursu |
| Skala problemu: UTK, Sprawozdanie i Raport 2025; Eurostat 12.2025 | 121, 68,4%, 115-121, 116 z 492 | SBR Tab. 9 s. 23, s. 25; Raport UTK za 2025 (CSI: 116 -> 118); Eurostat "Table 1" | zob. slajdy 2, 3, 11 |
| Koszty i przepisy: CUPT 2026; Dz.U. 2025 poz. 1105; PLK Id-1, Tom XIV | 4,3 mln zł; kat. E; D2, OTDZ; zał. 1 | CUPT Z41; Dz.U. 2025 poz. 1105 (§ 5, § 11); Id-1 D2, D3; Tom XIV zał. 1 s. 18 | zob. slajdy 3, 5, 8, 10, 15, 16 |
| Stan rejestrów: NIK, P/16/029 | 51 wobec 43; kontrola 2015-2016 | NIK s. 8, s. 35 | zob. slajd 5 |
| Skuteczność środków: RESTRAIL, FRA, RSSB, badania z Finlandii i Szwecji | stoją za katalogiem środków | literatura w sekcji 4; `dane/interventions.json`; karty top-20 | na slajdach nie ma liczb skuteczności; slajd 10 cytuje tylko obserwację o przesunięciu ruchu |
| DINOv2 (Meta) · Apache-2.0 | rozpoznawanie obrazu | karta modelu facebook/dinov2-small (Hugging Face) | odczyt |
| Python i biblioteki open source · BSD, MIT, Apache-2.0 | Python PSF; numpy, pandas, scipy, scikit-learn, geopandas, shapely, networkx, PyTorch BSD-3-Clause; pyproj, pyogrio, openpyxl, python-pptx, GDAL, PROJ MIT; Pillow MIT-CMU; pyosmium BSD-2-Clause; requests, Transformers, Playwright, uv Apache-2.0 (uv także MIT); curl_cffi, beautifulsoup4 MIT, trafilatura Apache-2.0 | metadane pakietów w PyPI (sprawdzone 19.11.2026); `kod/requirements.txt` (część narzędzi z tej listy, np. Playwright, python-pptx, uv, służyła do przygotowania prezentacji i zrzutów i nie jest w publicznym kodzie) | odczyt metadanych; PyTorch ma w metadanych zbiór licencji składników, licencja główna BSD-3-Clause; GDAL, PROJ i Python: wiedza o licencjach projektu, bez ponownego otwarcia plików 19.11 |
| Leaflet, podkład Esri · BSD-2, warunki Esri | Leaflet 1.9.4 BSD-2-Clause; podkład Esri World Light Gray Canvas | LICENSE Leaflet 1.9.4 (GitHub); warunki Esri | odczyt; podkład tylko w demo, z atrybucją |
| Inter, IBM Plex, ikony Carbon · SIL OFL 1.1, Apache-2.0 | czcionki Inter i IBM Plex SIL OFL 1.1; ikony Carbon Apache-2.0 | licencje projektów (wiedza, bez ponownego otwarcia plików 19.11) | odczyt |
| "Audyt: pełna lista liczb z prezentacji z adresami" | ten plik | `zrodla-i-liczby.md` | sekcje 1 (liczby) i 4 (adresy) |

### Slajd 19 - dziękujemy

| Liczba / twierdzenie | Wartość | Źródło | Jak policzone |
|---|---|---|---|
| Autorzy, uczelnia, kontakt | dane na slajdzie | decyzja autorów | brak liczb; w tym pliku bez danych osobowych |
| Wyzwanie nr 2: Czy AI może przewidzieć zagrożenie? | nr 2 | Regulamin § 4 ust. 2 pkt 2 | zob. slajd 1 |
| Liczba slajdów | 19 (limit 20) | Regulamin § 5 ust. 3 | zliczenie stron PDF |
| Demo jako materiał uzupełniający | `demo/Dzika_Sciezka_demo.html` | Regulamin § 5 ust. 4 | cytat: "kod źródłowy ... lub link do wersji demonstracyjnej" |

## 2. Założenia autorów

Wartości wybrane przez zespół, nie wzięte z danych ani literatury.

- **Nadzór ZLK (slajdy 6, 8, 13)**: proponowany proces docelowy (zatwierdza pracownik PLK), oparty na istniejących mechanizmach Id-1 D2 (obchód, OTDZ, Arkusz Dozorowania); PLK nie wdrożyła takiego systemu.
- **Coroczna runda (slajd 8)**: zdjęcia GUGiK są odnawiane cyklicznie, ale nierównomiernie; "co roku" to propozycja.
- **Oczekiwana zmiana (slajd 11)**: mniej interwencji SOK, koniec stałej liczby ofiar i niższa pozycja w Eurostacie to oczekiwania i proponowane miary, bez celów liczbowych.
- **Ogrodzenie wsparcia 26-134 tys. zł (slajd 15)**: założenie 2 x 100 m ogrodzenia kanalizującego (min. 100 m wg Clapperton) po 130-670 zł/mb.
- **Tablice 0,6-4 tys. zł (slajd 15)**: 2 tablice na miejsce, ceny z cennika budżetu obywatelskiego (tabliczka 300-700 zł, tablica wolnostojąca 1 200-2 000 zł).
- **Dojście do peronu od 82 tys. zł (katalog, miejsca 9 i 16)**: chodnik 100 m x 2 m x 410 zł/m2; górna granica to realizacja PLK z chodnikami (Warszawa Wileńska).
- **Patrol SOK (slajd 15)**: okno 18-23 z SBR s. 58; koszt ok. 14,9 tys. zł/rok w katalogu (I11) to rząd wielkości, nie oferta; kwota nie występuje na slajdach.
- **Wagi H 0,4 / 0,4 / 0,2, progi p95, progi D 100 m / 1 500 m (slajd 9)**: wybrane przez autorów; test czułości (30 wariantów, 2 000 losowań) pokazuje 17 z 20 miejsc stabilnych (wynik nie jest na slajdach).
- **Definicja dzikiego przejścia (slajd 7)**: definicja robocza zespołu, spójna z kategorią UTK nr 34.
- **Etap 2**: założenie, że model wizyjny nauczony na wykazach ZLK i SOK będzie lepszy (slajd 12); weryfikacja możliwa dopiero po otrzymaniu danych.
- **Dane przykładowe w demo (slajdy 14-16)**: wartości w zrzutach pochodzą z danych projektu; pola formularza (numer AD, osoba, data, wpis Z-0001) są wymyślone do zrzutu.

## 3. Decyzje metodyczne

- **Wzór i wagi (slajd 9).** Wynik = 100 x pierwiastek 3. stopnia z (E x D x H), średnia geometryczna czynników 0-1 z równymi wagami. Ranking jest identyczny z rankingiem po iloczynie, pierwiastek tylko rozkłada liczby na skali 0-100. Czynnik zerowy zeruje wynik (nikt nie mieszka obok, legalne przejście tuż obok). Alternatywa addytywna pozwalałaby, by duży jeden czynnik maskował brak pozostałych. Manganowa: 0,4758^(1/3) = 0,7807, wynik 78,1; Słupska: 0,1500^(1/3) = 0,531, wynik 53,1.
- **E, ekspozycja.** E = sqrt(min(1, cross_demand / 30 090,7)); cross_demand = ludność A x rodzaje celów B + ludność B x rodzaje celów A (500 m, ok. 6 min pieszo). Liczba rodzajów celów (przystanek, szkoła, sklep, praca, działki, park, sport, zabudowa), nie punktów, żeby jedno centrum handlowe z 127 sklepami nie zniekształcało listy. Pierwiastek i obcięcie na p95 hamują dominację jednego osiedla.
- **D, progi 100 m / 1 500 m.** D = clip((nadkład - 100) / 1400, 0, 1); nadkład = trasa legalna minus skrót. Dolny próg 100 m: kontrola na 40 legalnych przejściach dała medianę stosunku 1,15, czyli nadkład ok. 10 m przy skrócie 60 m; 100 m to ok. 10 razy tyle. Górny próg 1 500 m = ok. 18 minut dodatkowo przy 5 km/h, powyżej motywacja do skrótu jest jednakowo silna (27 z 82 kandydatów nasyca się na D = 1). Próg 300 m (Silla i Luoma 2011) rozdziela tanie ogrodzenie od legalnego przejścia.
- **Limit D przy dużych węzłach (yard cap).** Przy >= 5 torach D <= 0,5: na stacjach punkty przesunięte o 30 m mogą wylądować za inną linią, a legalne przejścia na stacjach miały stosunek dróg do 25, więc objazd jest tam mniej wiarygodny. Dotyczy 9 kandydatów (m.in. Kleczkowska, Żernicka, Krzywoustego, Wojska Polskiego); test z limitem wyłączonym lub od 3 torów zmienia top-20 najwyżej o 1 miejsce.
- **H, zagrożenie.** H = 0,4 x v/160 + 0,4 x sqrt(pociągi/146) + 0,2 x tory/3. Suma ważona, żeby linie z samym ruchem towarowym (0 pociągów pasażerskich) nadal dostawały część z prędkości i torów. Prędkość odniesiona do 160 km/h (limit przejść w poziomie szyn, Dz.U. 2025 poz. 1105 § 5), tory obcięte na 3 (powyżej wymagany system przejazdowy, § 11 ust. 2), pociągi: pierwiastek z p95 = 146/dobę. Manganowa: 0,150 + 0,2924 + 0,1333 = 0,576; Słupska: 0,400 + 0,321 + 0,133 = 0,854.
- **Zamrożone p95.** Progi p95 (ekspozycji 30 090,7 i pociągów 146) policzono na pierwszych 86 kandydatach i zamrożono w `score.py`, żeby usunięcie 4 punktów nie przesunęło skali.
- **Scalanie miejsc w promieniu 300 m.** Kandydaci w odległości <= 300 m to jedno miejsce (zachłannie, wiodący = najwyższy wynik). 300 m to promień przesunięcia z badań interwencji: jedno ogrodzenie lub jedno legalne przejście obsługuje sąsiadów. Daje 82 kandydatów i 63 miejsca; top-20 miejsc obejmuje 31 punktów. Słupska (T1-0042) jest wiodącym punktem miejsca nr 13 (trzy punkty).
- **Zakres ekspozycji 500 m.** Spójnie dla ludności i celów, ok. 6 minut spaceru; połówki dysku po obu stronach toru wyznaczone lokalną styczną (+/-25 m). Dla zakrętów i węzłów przypisanie strony jest przybliżone.
- **Walidacja (poza prezentacją, w repozytorium).** 23 potrącenia z prasy lokalnej (Wrocław, 2016-2026; spośród 28 użytecznych, 23 w obszarze Wrocławia), bez zdarzeń z podejrzeniem samobójstwa. Przy top-20 miejsc: 4 z 23 (17%) wobec 5,7% dla losowych punktów na torach (10 000 losowań), p = 0,04; przy mocniejszym baseline (tory w 1 000 m od kandydata) 12,3% i p = 0,31; 16 z 23 potrąceń bez kandydata w promieniu. Zdarzenia nie uczą modelu, tylko sprawdzają ranking. Wniosek ostrożny: kierunek tak, dowodu brak. Prezentacja nie podaje tych wyników (slajd 12 mówi tylko o "rankingu sprawdzonym na pełnych danych" jako celu). Wyniki w `dane/t6_validation.json` policzono na współrzędnych zdarzeń przed zaokrągleniem; `kod/t6_scoring/validate.py` uruchomiony na opublikowanym, zaokrąglonym `dane/validation.geojson` daje te same wyniki główne, a różni się odległościami do kandydatów o kilkadziesiąt metrów i jedną statystyką pomocniczą (`flat_300m`: n = 8 zamiast 7, p = 0,056 zamiast 0,079).
- **Czułość (poza prezentacją).** 30 wariantów i 2 000 losowań (U(0,5; 1,5) x wartość bazowa): mediana 17 z 20 miejsc zostaje w top-20 (liczone na 86 kandydatach przed usunięciem 4 punktów; `dane/t6_sensitivity.json`).
- **Model wizyjny (poza prezentacją; slajdy 6, 7, 13, 16).** DINOv2 ViT-S/14 bez dostrajania, regresja logistyczna C = 0,05, walidacja blokowa 2 x 2 km; 51 pozytywów (26 punktów T1 + 11 z tagu OSM + 14 ścieżek "informal"), 599 losowych negatywów; ROC-AUC na łatwych negatywach 0,946-0,965 (średnia 5 powtórzeń 0,958), z trudnymi negatywami ok. 0,91 (`cv_report_round1.json`, `cv_report_round2.json`). Skan: 3 143 kadry zawężone do 40 wskazań; po obejrzeniu: 2 potwierdzone, 9 niepewnych, 29 fałszywych (`labels_top40_round1.json`); do demo trafiło 12 wykryć (11 z rundy 1 plus 1 z rundy 2): 2 potwierdzone, 10 niepewnych. Sam model nie decyduje i nie przewiduje wypadków (brak istotnej zależności od potrąceń, p > 0,1, n = 23). Wynik to miejsca, nie ludzie: bez danych osobowych i kamer.
- **Dobór środka (slajd 10).** Najtańszy środek z uzasadnieniem: ogrodzenie tylko gdy legalna droga <= 300 m (warunek badania Silla i Luoma), legalne przejście kat. E przy dłuższym objeździe do 3 torów i 160 km/h, kładka lub tunel przy więcej niż 3 torach, patrol i tablice zawsze jako środek od zaraz. Katalog: 15 środków w `dane/interventions.json`. W top-20 żaden objazd nie jest <= 300 m (min 473,8 m, Słupska), więc ogrodzenie występuje tylko jako wsparcie. Suma środków głównych dla top-20: 21-87 mln zł (6 x 3,5-11 mln zł kładki, 12 x 14 tys.-1,5 mln zł przejścia kat. E, 2 x 82 tys.-1,5 mln zł dojścia do peronu; `primary_cost_min_pln`, `primary_cost_max_pln`); kwota nie występuje na slajdach.

## 4. Źródła

Ścieżki lokalne dotyczą plików w repozytorium. Surowe pobrania (pliki OSM, siatka GUS, GTFS, Regulamin sieci, kafle ortofotomapy) nie są w repozytorium; komendy i adresy do ich odtworzenia: `dane/README.md`.

### Dokumenty urzędowe i statystyki

- UTK, Sprawozdanie ze stanu bezpieczeństwa ruchu kolejowego 2025 (Tab. 9 s. 23, s. 25, s. 56 i Tab. 14, s. 58, s. 60): https://utk.gov.pl/download/1/128688/Sprawozdaniezestanubezpieczenstwaruchukolejowego2025.pdf
- UTK, Raport w sprawie bezpieczeństwa za 2025 (osoby nieupoważnione wg CSI, s. 6 i s. 38): https://dziennikurzedowy.utk.gov.pl/download/6/3436/Raportwsprawiebezpieczenstwaza2025-sig.pdf
- NIK, Bezpieczeństwo ruchu na przejściach i przejazdach kolejowo-drogowych, P/16/029 (nr ewid. 200/2016/P/16/029/KIN, marzec 2017; s. 8 okres kontroli, s. 35 wykazy dzikich przejść): https://www.nik.gov.pl/plik/id,12954,vp,15363.pdf
- Dz.U. 2025 poz. 1105, rozporządzenie MI z 9.07.2025 (przejazdy kolejowo-drogowe i przejścia; § 5, § 11): https://api.sejm.gov.pl/eli/acts/DU/2025/1105/text.pdf
- Prawo geodezyjne i kartograficzne, tekst jednolity Dz.U. 2026 poz. 1389 (art. 40a ust. 2 pkt 1 lit. e): https://api.sejm.gov.pl/eli/acts/DU/2026/1389/text.pdf
- Regulamin konkursu "Kolej na bezpieczeństwo", II edycja (§ 4 ust. 2, § 5 ust. 2-4), wersja z 16.11.2026, opublikowana przez PKP PLK na stronie konkursu
- CUPT, koszty jednostkowe (ver. 2026-05-28; arkusz "Wypadki", komórka Z41): https://www.cupt.gov.pl/wp-content/uploads/2026/07/upload_koszty-jednostkowe_ver2026-05-28_14709_280.xlsx
- CUPT, wytyczne analizy kosztów i korzyści, kolej 2023: https://www.cupt.gov.pl/wp-content/uploads/2023/04/upload_nk-kolej-2023-pl_3153_623.pdf
- Eurostat, Rail accidents and fatalities (Statistics Explained, 12.2025; arkusz "Table 1", kod zbioru tran_sf_railvi): https://ec.europa.eu/eurostat/statistics-explained/images/f/f5/Rail_accidents_and_fatalities_2025-12.xlsx

### Dokumenty PLK

- PLK, Id-1 (uchwała 1037/2025), Moduł D2 "Diagnostyka - dozorowanie" (§ 9 s. 10, § 15 s. 18), Zał. 1 D2AD (kod OTDZ) oraz Moduł D3 (tabela 1, stopnie U1-U4): https://www.plk-sa.pl/files/public/user_upload/pdf/Akty_prawne_i_przepisy/Instrukcje/Wydruk/Id/Id-1_uz_1037_25.zip
- PLK, Standardy Techniczne Tom XIV, Załącznik nr 1 (s. 18-19, model decyzyjny wygrodzeń): https://www.plk-sa.pl/files/public/user_upload/pdf/Akty_prawne_i_przepisy/Standardy_techniczne/11.04.2022/Standardy_Techniczne_TOM_XIV_WCAG.pdf
- PLK, Regulamin sieci 2025/2026, zał. 1, 2.1, 2.6, 2.12 (pliki nie są w repozytorium): https://www.plk-sa.pl/files/public/user_upload/pdf/Reg_przydzielania_tras/Regulamin_sieci_2025-2026/v.42/N_ZAL_2.1_20252026_20261008065031.xlsx
- PLK, warunki ponownego wykorzystywania informacji: https://bip.plk-sa.pl/ponowne-wykorzystywanie
- PLK, Otwarte Dane Kolejowe (API): https://pdp-api.plk-sa.pl/

### Dane przestrzenne

- OpenStreetMap, Overpass API (ODbL 1.0): https://overpass-api.de/api/interpreter
- Geofabrik, ekstrakt Dolnego Śląska z 13.11.2026: https://download.geofabrik.de/europe/poland/dolnoslaskie-261113.osm.pbf
- GUS, NSP 2021, siatka 250 m: https://geo.stat.gov.pl/atom-web/atom/GRID
- GUGiK, ortofotomapa (WMS Geoportal): https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution
- PolishTrainsGTFS (M. Kuranowski): https://github.com/MKuranowski/PolishTrainsGTFS (dane: https://mkuran.pl/gtfs/polish_trains.zip)

### Literatura i opracowania o skuteczności środków

Te prace stoją za katalogiem środków (`dane/interventions.json`, karty top-20); na slajdach nie podajemy z nich liczb (slajd 10 cytuje obserwację o przesunięciu ruchu).

- Silla, A., Luoma, J. (2011), Accident Analysis and Prevention 43(3):1089-1094; pełny raport VTT S27 (Finlandia): https://publications.vtt.fi/pdf/science/2012/S27.pdf
- Fredin-Knutzén i in. (2024), Journal of Safety Research 88:78-84 (Sztokholm; opis w FRA Trespass Toolkit L00026): https://trespasstoolkit.fra.dot.gov/eLib/Details/L00026
- Kallberg, V.-P., Silla, A. (2017), Finlandia, czujnik IR z komunikatem (wyniki ze streszczeń i FRA Toolkit)
- RESTRAIL, podręcznik: https://www.restrail.eu/IMG/pdf/restrail_book.pdf
- FRA Trespass Toolkit (L00033, L00037, L00026, L00040, L00053, L00062): https://trespasstoolkit.fra.dot.gov/eLib/
- FDOT-CFRC, Trespass Report (01.2020; cytat o przesunięciu ruchu, slajd 10): https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/rail/publications/studies/safety/fdot-cfrc-final-trespass-report-01202020.pdf
- RSSB, Impact evaluation (ocena skutków interwencji, miejsce kontrolne; przesunięcie na inne odcinki): https://www.rssb.co.uk/safety-and-health/trespass-and-suicide/trespass-and-suicide-one-stop-shop/risk-management-for-trespass-and-suicide-prevention/tackling-trespass-risk/planning-evaluation/assessing-results/impact-evaluation

### Koszty środków (zrzut karty, slajd 15)

- Przetarg SKM SKMMU.086.38.21, informacja z otwarcia ofert (ogrodzenie): https://www.skm.pkp.pl/files/user-uploads/przetargi/07.09.2021-inf._z_otwarcia_ofert_ogrodzenie.pdf
- Legionowo, przejście Piaski (2012): https://legionowo.pl/a/4208-piaski-bezpieczne-przejscie-przez-tory
- Rynek Kolejowy, przejście przy Warszawie Wileńskiej (1.02.2025): https://www.rynek-kolejowy.pl/wiadomosci/pkp-plk-otworzyly-przejscie-dla-pieszych-przy-dworcu-wilenskim-142338.html
- PLK, kładka w Lubartowie: https://www.plk-sa.pl/o-spolce/biuro-prasowe/informacje-prasowe/szczegoly/nowe-bezpieczne-przejscie-nad-torem-w-lubartowie-8837
- PLK, kładka w Sosnowcu: https://www.plk-sa.pl/o-spolce/biuro-prasowe/informacje-prasowe/szczegoly/dla-bezpieczenstwa-mieszkancow-wybudujemy-kladke-nad-torami-w-sosnowcu-11266
- Cennik miejski, budżet obywatelski Koszalin (tabliczki, tablice, chodniki): https://koszalin.budzetobywatelski.pl/wszystko-o-budzecie/cennik-miejski
- Pełna lista źródeł kosztów kładek, ogrodzeń i patroli: pola `cost_source` w `dane/interventions.json` (znaczniki [OPENED] = źródło otwarte i sprawdzone, [SNIPPET] = tylko streszczenie, [UNVERIFIED] = bez wiarygodnej ceny)

### Modele i oprogramowanie

- DINOv2-small (Meta, Apache-2.0): https://huggingface.co/facebook/dinov2-small oraz https://github.com/facebookresearch/dinov2
- Leaflet 1.9.4 (BSD-2-Clause): https://github.com/leaflet/leaflet/blob/v1.9.4/LICENSE
- Zestawienie bibliotek i licencji: slajd 18 (sekcja 1); `kod/requirements.txt`

### Dane własne w repozytorium

- Ranking: `dane/ranking.csv`, `dane/ranking.geojson`; karty: `dane/top20/`; środki: `dane/interventions.json`; wykrycia AI: `dane/candidates_ai.geojson`; odcinki linii z ruchem i prędkością: `dane/rail_hazard.geojson`, `dane/rail_hazard_lines.csv`
- Model wizyjny: `dane/t1b/` (`cv_report_round1.json`, `cv_report_round2.json`, `labels_top40_round1.json`, `ortho_dates.json`, `scan_index.json`, `scan_all_index.json`, `hard_negatives_index.json`)
- Walidacja i czułość: `dane/t6_validation.json`, `dane/t6_validation_events.csv`, `dane/t6_sensitivity.json`, `dane/validation.geojson` (zanonimizowane)
- Demo: `demo/Dzika_Sciezka_demo.html` (dane w obiekcie `DATA`)
- Opis zdarzeń z prasy jest przechowywany lokalnie przez autorów i nie jest publikowany (w repozytorium tylko wynik zanonimizowany do roku i skutku)
