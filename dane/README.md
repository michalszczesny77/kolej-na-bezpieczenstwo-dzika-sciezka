# Dane

Wyniki projektu i małe dane wejściowe potrzebne do ich sprawdzenia. Każdy plik jest użyty w prezentacji, w demo albo w liczbach z [Źródła i liczby](../zrodla-i-liczby.md). Współrzędne w pliku `*.geojson` są w WGS84 (lon, lat), w plikach CSV jako kolumny `lat`, `lon`. Pliki pochodne od OpenStreetMap podlegają licencji ODbL 1.0 ((c) autorzy OpenStreetMap), pozostałe źródła zachowują własne warunki (kolumna "Licencja").

Skróty w kolumnie "Użycie": s. = slajd prezentacji, Z+L = [Źródła i liczby](../zrodla-i-liczby.md), demo = `demo/Dzika_Sciezka_demo.html`.

## Wyniki i dane wejściowe rankingu

| Plik | Co to jest | Najważniejsze kolumny / pola | Źródło i licencja | Użycie |
|---|---|---|---|---|
| `candidates.csv`, `candidates.geojson` | 82 kandydatów na dzikie przejścia (etap T1) | `id` (T1-xxxx), `lat`, `lon`, `sources` (reguła OSM, która znalazła punkt), `rail_ref` (numer linii), `nearest_official_m` (odległość do legalnego przejścia), `geoportal_url` | OpenStreetMap, ODbL 1.0; wynik `kod/t1_candidates/build_candidates.py` | s. 14; wejście `score.py` |
| `exposure/candidates_t3.geojson` | kandydaci z ekspozycją i objazdem (etap T3) | `pop_500m`, `pop_500m_a/b`, `n_<cel>_a/b` (liczba rodzajów celów), `detour_walk_m`, `detour_straight_m`, `legal_crossing_type` | OSM (ODbL 1.0), GUS NSP 2021 siatka 250 m (z podaniem źródła); wynik `kod/t3_exposure/` | s. 4, 9; wejście `score.py` |
| `rail_hazard.geojson`, `rail_hazard_lines.csv` | odcinki linii wokół Wrocławia z prędkością, torami i pociągami na dobę (etap T2); `..._lines.csv` to zestawienie na linię | `line_no`, `km_from`, `km_to`, `vmax_kmh`, `tracks`, `trains_per_day`, `*_source` | OSM (ODbL 1.0), PLK Regulamin sieci 2025/2026 zał. 2.1 i 2.12 (dokument publiczny PLK), PolishTrainsGTFS (geometrie CC0 1.0, rozkłady wg przewoźników) | s. 9, 15, 16 |
| `ranking.csv`, `ranking.geojson` | ranking 82 kandydatów i 63 miejsc, wynik 0-100, zalecany środek | `score`, `rank`, `place_rank`, `place_leader`, `E_exposure`, `D_detour`, `H_hazard`, `street`, `station`, `line_nearest`, `vmax_kmh`, `trains_per_day`, `pop_500m`, `detour_walk_m`, `rule`, `intervention_primary`, `primary_cost_text`, `flags` | wynik własny z powyższych; ODbL 1.0 (część pochodna OSM) | s. 1, 4, 9, 10, 14, 15; demo |
| `interventions.json` | katalog 15 środków z kosztami i źródłami | `id`, `name_pl`, `cost_pln_min/max`, `unit`, `cost_source` (znaczniki [OPENED], [SNIPPET], [UNVERIFIED] = poziom sprawdzenia źródła), `effect_source`, `conditions` | ceny i badania z publicznych źródeł (adresy w polach `*_source` i w Z+L, sekcja 4) | s. 1, 10, 15; Z+L sekcja 3 |
| `top20/` | karty 20 najgroźniejszych miejsc: `NN_<id>.md` (wynik, powód, zalecenie, stabilność) i `NN_<id>.jpg` (ortofoto 300 x 300 m, czerwone kółko = kandydat), `index.md` | tekst własny; zdjęcia: ortofotomapa GUGiK (Geoportal), udostępniana bez opłat (art. 40a Prawa geodezyjnego i kartograficznego), źródło: GUGiK | s. 15; demo (zdjęcie w karcie miejsca) |
| `t6_sensitivity.json` | test czułości wag i progów (30 wariantów, 2 000 losowań) | `variants`, `top20_places_stability`, `monte_carlo`, `base_params` | wynik własny | karty top-20 (stabilność); Z+L sekcja 3 |
| `km_anchors.json` | kotwice kilometrażu linii (słupki OSM `railway=milestone` i stacje z Regulaminu sieci), do podania km na karcie | `lines` (numer linii: lista [km, lat, lon]), `max_gap_m`, `check` | OSM, ODbL 1.0, PLK Regulamin sieci zał. 1; wynik `kod/t7_demo/km_anchors.py` | s. 15; demo |

## Wykrycia AI (etap T1b)

| Plik | Co to jest | Najważniejsze kolumny / pola | Źródło i licencja | Użycie |
|---|---|---|---|---|
| `candidates_ai.geojson` | 12 wykryć AI po przeglądzie zdjęć | `id` (AI-xxx), `ai_score`, `verified_label` (real / unsure), `verified_note`, `rail_line_no`, `nearest_official_m`, `ortho_date`, `geoportal_url` | model DINOv2-small (Apache-2.0) + ortofotomapa GUGiK; wynik własny | s. 5, 16; demo (zakładka Wykrycia AI) |
| `t1b/cv_report_round1.json`, `cv_report_round2.json` | walidacja modelu (ROC-AUC, 2 x 2 km), liczby kadrów skanu | `scan.n_tiles`, metryki | wynik własny | s. 7, 13; Z+L sekcja 3 |
| `t1b/scan_all_index.json`, `scan_index.json` | punkty skanu co 60 m wzdłuż linii (4 480) i kadry po filtrze ludności (3 143) | `tile_id`, `lat`, `lon`, `line_no`, `pop500` | OSM (ODbL 1.0), GUS | s. 7 |
| `t1b/hard_negatives_index.json` | trudne negatywy (perony, przejścia dwupoziomowe) użyte w uczeniu | `tile_id`, `hard` | OSM (ODbL 1.0) | s. 7 |
| `t1b/ortho_dates.json` | daty zdjęć lotniczych w siatce komórek | `cells`, `tiles` | GUGiK (metadane ortofotomapy) | s. 1, 16, 17 |
| `t1b/labels_*.json` | ręczne etykiety zespołu: pozytywy, negatywy, przegląd 40 wskazań w dwóch rundach | `labels` | wynik własny (oglądanie zdjęć) | s. 7, 16; wejście `train.py` |
| `t1b/validation_events.json` | zdarzenia (rok, przybliżone miejsce) do sprawdzenia, czy model przesiewa miejsca z wypadkami; współrzędne zaokrąglone do 3 miejsc po przecinku | `id`, `lat`, `lon`, `radius`, `precision` | patrz Walidacja niżej | s. 13; wejście `eval_events.py` |

## Walidacja zdarzeniami (zanonimizowana)

| Plik | Co to jest | Najważniejsze kolumny / pola | Źródło i licencja | Użycie |
|---|---|---|---|---|
| `validation.geojson` | 28 użytecznych potrąceń z regionu (rok, skutek, przybliżone miejsce) oraz 8 punktów OSM `hazard=illegal_crossing` | `year`, `outcome`, `precision`, `uncertainty_m`, `use_for_validation`; współrzędne zaokrąglone do 3 miejsc po przecinku (ok. 100 m) | zdarzenia ustalone z doniesień prasy lokalnej; nie zawiera nazwisk, cytatów, adresów URL ani okoliczności; punkty OSM: ODbL 1.0 | wejście `validate.py`; Z+L sekcja 3 |
| `t6_validation.json`, `t6_validation_events.csv` | wynik porównania rankingu ze zdarzeniami (23 zdarzenia w obszarze Wrocławia): trafienia, test permutacyjny, najbliższy kandydat | `accidents`, `osm_hazard_tag_ranks`; w CSV `event_id`, `date` (rok), `nearest_candidate`, `nearest_m`, `any_candidate_in_300m` | wynik własny, policzony przed zaokrągleniem współrzędnych; ponowne uruchomienie `validate.py` na zaokrąglonym pliku daje te same wyniki główne, a odległości różnią się o kilkadziesiąt metrów (jedna statystyka pomocnicza: `flat_300m`, n = 8, p = 0,056 zamiast n = 7, p = 0,079) | s. 12, 13 (bez liczb), 15 ("Zdarzenia w 300 m"); demo |

## Małe dane surowe (OSM)

| Plik | Co to jest | Źródło i licencja | Użycie |
|---|---|---|---|
| `raw/wro_platforms.json` | perony w okolicy Wrocławia (Overpass) | OSM, ODbL 1.0 | `score.py` (odległość do peronu, zalecenie "dojście do peronu") |
| `raw/wro_crossings_hazard.json` | legalne przejścia i oznaczenia hazard w okolicy Wrocławia (Overpass) | OSM, ODbL 1.0 | demo (warstwa legalnych przejść) |
| `raw/osm_illegal_crossing_PL.json` | węzły `hazard=illegal_crossing` w Polsce (Overpass) | OSM, ODbL 1.0 | `build_candidates.py` (kandydaci z tagu), etykiety AI |

## Czego nie ma w repozytorium i jak to odtworzyć

Duże pliki surowe i pośrednie nie są w repozytorium (łącznie kilkaset MB). Wyniki z tabel powyżej są kompletne i wystarczą do obejrzenia i sprawdzenia rankingu, kart i dema. Do przeliczenia od zera pobierz:

| Dane | Skąd | Gdzie położyć |
|---|---|---|
| OSM: tory, drogi, perony, przejścia | `python kod/t1_candidates/fetch_osm.py`, `python kod/t2_hazard/fetch_osm.py` (Overpass API, https://overpass-api.de/api/interpreter) | `raw/` (m.in. `wro_rails.json`, `wro_highways_tiles/`, `osm_rail_wro/overpass_rail_wro.json`) |
| Ekstrakt OSM Dolnego Śląska z 13.11.2026 | https://download.geofabrik.de/europe/poland/dolnoslaskie-261113.osm.pbf (Geofabrik trzyma tylko ostatnie dni; wersja `-latest` daje nieco inne wyniki) | `raw/t3_osm/` |
| GUS, NSP 2021, siatka 250 m | https://geo.stat.gov.pl/atom-web/atom/GRID (plik `NSP2021_TOT_GRID250m_GPKG.zip`) | rozpakować do `raw/t3_gus/grid250/` |
| Rozkłady jazdy PolishTrainsGTFS (stan z 18.11.2026) | https://mkuran.pl/gtfs/polish_trains.zip (kod i opis: https://github.com/MKuranowski/PolishTrainsGTFS); feed zmienia się codziennie, więc liczba pociągów z innego dnia będzie nieco inna | rozpakować do `raw/gtfs_polish_trains/extracted/` |
| PLK, Regulamin sieci 2025/2026, załączniki 1, 2.1, 2.6, 2.12 (v.41/v.42) | adresy w [Źródła i liczby](../zrodla-i-liczby.md), sekcja 4 | `raw/plk_regulamin_sieci_2025_2026/` |
| Kafle ortofotomapy (Geoportal WMS) | pobierają je skrypty `kod/t1_candidates/ortho_check.py`, `kod/t1b_ortho_ai/fetch_tiles.py` i `kod/t6_scoring/cards.py` | `raw/ortho_tiles/`, `t1_ortho_check/` |
| Model DINOv2-small | pobierany automatycznie przez `kod/t1b_ortho_ai/embed.py` (Hugging Face) | pamięć podręczna Hugging Face |

Pliki pośrednie odtwarzane skryptami z `kod/`: graf pieszy `exposure/walk_graph.gpkg` (ok. 107 MB), siatka ludności, atraktory (OSM), embeddingi modelu (`t1b/embeddings_dinov2s.npz`, ok. 16 MB), wyniki skanu (`t1b/scan_scores_round*.json`).

Uwagi o odtwarzalności:

- `kod/t6_scoring/score.py` uruchomiony na 82 kandydatach odtwarza wyniki i kolejność miejsc z `ranking.csv`. `ranking.csv` powstał z przebiegu na 86 kandydatach i został przycięty do 82 (usunięcie reguły `geometric_intersection`), więc kolumny pomocnicze (`exposure_level` dla dwóch miejsc, `stable_top`, `top20_share_mc`, kilka flag, środek zalecany dla miejsca 44) różnią się w nowym przebiegu; szczegóły w [Źródła i liczby](../zrodla-i-liczby.md), sekcja 3.
- Zdarzenia użyte do walidacji pochodzą z doniesień prasy lokalnej, które zostają u autorów (dane dotyczą konkretnych osób). Skrypt, który je zbierał, nie jest publikowany; opublikowany jest tylko zanonimizowany wynik.
- Skrypty wyznaczają ścieżki względem własnego położenia i zakładają układ repozytorium: `kod/` obok `dane/` i `demo/`.
