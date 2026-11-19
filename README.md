# Dzika Ścieżka

Ranking dzikich (nielegalnych) przejść przez tory we Wrocławiu i aglomeracji, z jawnym wzorem, kartą każdego miejsca i tanim zaleceniem. Praca na konkurs studencki PKP PLK "Kolej na bezpieczeństwo", II edycja, wyzwanie nr 2: "Czy AI może przewidzieć zagrożenie?".

Autorzy: Maria Płatek i Michał Szczęsny, Politechnika Wrocławska.

## Materiały

| Materiał | Plik |
|---|---|
| Prezentacja (19 slajdów, PDF) | [`prezentacja/Dzika_Sciezka.pdf`](prezentacja/Dzika_Sciezka.pdf) |
| Demo (jeden plik HTML) | [`demo/Dzika_Sciezka_demo.html`](demo/Dzika_Sciezka_demo.html) |
| Film | [`film/Dzika_Sciezka_film.mp4`](film/Dzika_Sciezka_film.mp4) |
| Skąd każda liczba z prezentacji | [`zrodla-i-liczby.md`](zrodla-i-liczby.md) |
| Opis danych | [`dane/README.md`](dane/README.md) |

## Co to jest

W 2025 r. na polskich torach zginęło 121 osób nieupoważnionych (68,4% wszystkich zabitych w wypadkach kolejowych, źródło: UTK). Nie znaleźliśmy jednej, jawnej mapy miejsc, w których ludzie przechodzą przez tory poza przejściami. Projekt buduje taką listę z danych otwartych: znajduje kandydatów, ocenia ich ryzyko i wskazuje najtańszy skuteczny środek. Wrocław to studium przypadku: 82 kandydatów, 63 miejsca w rankingu, 20 najgroźniejszych z kartą i zaleceniem. Dane wejściowe są krajowe, więc ten sam proces można powtórzyć dla innego zakładu linii (nie testowano poza Wrocławiem).

Wynik miejsca = 100 x (E x D x H)^(1/3), czynniki w skali 0-1:

- E, ekspozycja: ilu ludzi ma powód przejść (ludność z siatki GUS i rodzaje celów z OSM w 500 m po obu stronach toru),
- D, objazd: o ile dalej jest legalne przejście (graf pieszy z OSM),
- H, zagrożenie: prędkość, liczba pociągów i tory (Regulamin sieci PLK, rozkłady GTFS, OSM).

Model wizyjny (DINOv2 + regresja logistyczna) przesiewa ortofotomapę i wskazuje 12 miejsc do sprawdzenia; nie wchodzi do rankingu, a każde wykrycie wymaga potwierdzenia przez człowieka.

## Demo

Otwórz [`demo/Dzika_Sciezka_demo.html`](demo/Dzika_Sciezka_demo.html) w przeglądarce (dwuklik, bez instalacji). Do wyświetlenia podkładu mapy (Esri) i ortofotomapy (Geoportal) potrzebny jest internet. W demo: ranking jako tabela z wyszukiwarką, mapa, karta miejsca, weryfikacja wykryć AI i okno "Jak liczymy". Karta konkretnego miejsca otwiera się po dopisaniu do adresu np. `#T1-0060`.

## Metoda

| Etap | Folder | Co robi |
|---|---|---|
| T1 | `kod/t1_candidates/` | kandydaci z OpenStreetMap (ślepe ścieżki, wspólne węzły, tagi), kontrola na ortofotomapie |
| T1b | `kod/t1b_ortho_ai/` | model wizyjny przesiewa kadry ortofotomapy 100 x 100 m do ręcznej weryfikacji |
| T2 | `kod/t2_hazard/` | zagrożenie na liniach: prędkość, tory, pociągi na dobę |
| T3 | `kod/t3_exposure/` | ekspozycja i objazd do najbliższego legalnego przejścia |
| T4-T5 | (poza kodem) | zdarzenia do walidacji (tylko wynik zanonimizowany) i przegląd przepisów, opisane w [`zrodla-i-liczby.md`](zrodla-i-liczby.md) |
| T6 | `kod/t6_scoring/` | wynik, ranking, test czułości, walidacja, karty top 20 |
| T7 | `kod/t7_demo/` | generator dema |

## Dane

Opis każdego pliku (kolumny, źródło, licencja, slajd lub element dema, który go używa): [`dane/README.md`](dane/README.md). Najważniejsze: `dane/ranking.csv` i `dane/ranking.geojson` (ranking), `dane/top20/` (karty 20 miejsc), `dane/candidates_ai.geojson` (wykrycia AI), `dane/interventions.json` (katalog 15 środków), `dane/rail_hazard.geojson` (zagrożenie na liniach).

Duże dane surowe (ekstrakt OSM, siatka GUS, GTFS, kafle ortofotomapy, graf pieszy) nie są w repozytorium; sposób ich pobrania jest w `dane/README.md`.

## Odtwarzanie

Python 3.12, `pip install -r kod/requirements.txt` (torch i transformers tylko dla kroku AI). Skrypty wyznaczają ścieżki względem własnego położenia (`kod/` obok `dane/`).

Bez pobierania danych surowych można uruchomić:

- `python kod/t6_scoring/validate.py` - porównanie rankingu ze zdarzeniami (na zanonimizowanym `dane/validation.geojson`),
- `python kod/t6_scoring/cards.py` - karty top 20 (pobiera kadry z Geoportalu, jeśli brakuje ich w `dane/top20/`),
- `python kod/t7_demo/build.py` - budowa `demo/Dzika_Sciezka_demo.html` z danych w `dane/` (wynik jest bajt w bajt taki sam jak dołączony plik).

Pełny przebieg od danych surowych (po pobraniu danych według `dane/README.md`):

1. `kod/t1_candidates/fetch_osm.py`, `kod/t2_hazard/fetch_osm.py` - pobranie OSM,
2. `kod/t1_candidates/build_candidates.py` - kandydaci,
3. `kod/t2_hazard/build_hazard.py` - zagrożenie na liniach,
4. `kod/t3_exposure/build_population.py`, `build_osm.py`, następnie `annotate.py` - ekspozycja i objazd,
5. `kod/t6_scoring/score.py` - ranking i test czułości; `cards.py` - karty,
6. `kod/t7_demo/km_anchors.py`, `kod/t7_demo/build.py` - kilometraż i demo,
7. opcjonalnie AI: `kod/t1b_ortho_ai/` w kolejności `build_index`, `fetch_tiles`, `extend_scan`, `fetch_extra_positives`, `build_extra_index`, `ortho_dates`, `embed`, `select_negatives`, `train`, `eval_events`, `finalize`.

Skrypty zbierające opisy zdarzeń z prasy nie są publikowane (patrz Prywatność). Zaokrąglone współrzędne zdarzeń w repozytorium dają te same wyniki główne walidacji co dane pełne; różnice opisano w `dane/README.md`.

## Licencje

- Kod (`kod/`): MIT, zob. [`LICENSE`](LICENSE).
- Dane pochodne od OpenStreetMap (kandydaci, graf, zagrożenie na liniach, ranking): ODbL 1.0, (c) autorzy OpenStreetMap.
- Pozostałe źródła na własnych warunkach: ortofotomapa GUGiK (udostępniana bez opłat, art. 40a Prawa geodezyjnego i kartograficznego, źródło: GUGiK), GUS NSP 2021 (z podaniem źródła), Regulamin sieci PLK i dokumenty UTK, NIK, CUPT, Eurostat (dokumenty publiczne, z podaniem źródła), PolishTrainsGTFS (geometrie CC0 1.0, rozkłady wg przewoźników), DINOv2-small (Apache-2.0), Leaflet (BSD-2-Clause), czcionki Inter, IBM Plex, Roboto, Barlow Condensed (SIL OFL 1.1 lub Apache-2.0) i ikony Carbon (Apache-2.0). Podkład mapy w demo: Esri, na warunkach Esri.
- Prezentacja, film i opisy: (c) 2026 Maria Płatek, Michał Szczęsny.
- Pełne zestawienie źródeł i adresów: [`zrodla-i-liczby.md`](zrodla-i-liczby.md).

## Prywatność

Projekt nie przetwarza danych osobowych. Z doniesień o zdarzeniach bierzemy tylko rok, skutek i przybliżone miejsce; nie publikujemy nazwisk, cytatów, adresów URL ani okoliczności. Współrzędne zdarzeń w plikach walidacyjnych są zaokrąglone do 3 miejsc po przecinku (ok. 100 m). Samobójstwa są poza zakresem projektu. Model wizyjny wskazuje miejsca na zdjęciach lotniczych, nie osoby.

## Autorzy

Maria Płatek i Michał Szczęsny, Politechnika Wrocławska.
