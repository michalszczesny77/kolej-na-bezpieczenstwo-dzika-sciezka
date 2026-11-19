import json
import math
import shutil
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "dane"
RANKING = DATA / "ranking.csv"
SENSITIVITY = DATA / "t6_sensitivity.json"
OUT = DATA / "top20"
T1_CROPS = DATA / "t1_ortho_check"
WMS = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution"
HALF_SIDE_M = 150
SIZE_PX = 800
TOP_N = 20

DEST_PL = {
    "transport": "przystanek lub stacja",
    "school": "szkoła lub przedszkole",
    "shop": "sklepy",
    "workplace": "zakłady pracy, biura",
    "allotments": "ogródki działkowe",
    "park": "park",
    "sport": "obiekty sportowe",
    "residential": "zabudowa mieszkaniowa",
}

FLAG_PL = {
    "korytarz_wielotorowy": "korytarz wielotorowy (3-4 tory do przejścia)",
    "stacja_lub_grupa_torow_objazd_ograniczony": "stacja lub grupa torów (5+ torów); czynnik objazdu ograniczony do 0,5, bo objazd liczony przez cały węzeł jest mniej pewny",
    "brak_toru_szlakowego_30m": "bocznica lub tor stacyjny: brak danych PLK o ruchu w promieniu 30 m",
    "tylko_towarowe_ruch_nieznany": "w promieniu 30 m tylko linie bez pociągów pasażerskich; ruch towarowy nieznany (brak publicznych danych), więc zagrożenie jest zaniżone",
    "brak_vmax": "brak prędkości w danych",
    "ryzyko_przesuniecia": "inne dzikie przejścia w promieniu 300 m: po zamknięciu jednego ruch może się przesunąć",
    "osm_hazard_illegal_crossing": "miejsce oznaczone przez społeczność OSM jako nielegalne przejście (hazard=illegal_crossing)",
}

CROSSING_PL = {"level_crossing": "przejazd lub przejście w poziomie torów", "grade_separated": "wiadukt, tunel lub kładka"}


def num(v, digits=0):
    s = f"{v:,.{digits}f}".replace(",", " ").replace(".", ",")
    return s


def dist(m):
    return f"{num(m)} m" if m < 1000 else f"{num(m / 1000, 1)} km"


def bbox_around(lat, lon):
    dlat = HALF_SIDE_M / 111320
    dlon = HALF_SIDE_M / (111320 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def crop(row, path):
    t1 = next(iter(T1_CROPS.glob(f"T1-*_{row.lat:.5f}_{row.lon:.5f}.jpg")), None)
    if t1:
        if not path.exists():
            shutil.copy(t1, path)
        return "pobrane z Geoportalu (WMS ORTO, StandardResolution)"
    if path.exists():
        return "pobrane z Geoportalu (WMS ORTO, StandardResolution)"
    params = {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap", "LAYERS": "Raster", "STYLES": "",
              "SRS": "EPSG:4326", "BBOX": ",".join(f"{v:.7f}" for v in bbox_around(row.lat, row.lon)),
              "WIDTH": SIZE_PX, "HEIGHT": SIZE_PX, "FORMAT": "image/jpeg"}
    for attempt in range(4):
        try:
            r = requests.get(WMS, params=params, headers={"User-Agent": "dzika-sciezka-research/1.0"}, timeout=120)
            if r.ok and r.headers.get("Content-Type", "").startswith("image"):
                path.write_bytes(r.content)
                img = Image.open(path).convert("RGB")
                c, rad = SIZE_PX // 2, 18
                ImageDraw.Draw(img).ellipse([c - rad, c - rad, c + rad, c + rad], outline=(255, 0, 0), width=3)
                img.save(path, quality=90)
                return "pobrane z Geoportalu (WMS ORTO, StandardResolution)"
        except requests.RequestException as exc:
            print(f"{row.id}: {exc}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    return None


def dest_text(lst):
    if not isinstance(lst, str) or not lst:
        return "brak celów w OSM"
    return ", ".join(DEST_PL[k] for k in lst.split(","))


def lines_text(r):
    lines = r.lines_30m if isinstance(r.lines_30m, str) and r.lines_30m else r.line_nearest
    if not isinstance(lines, str) or not lines or lines == "nan":
        return "bocznica bez numeru linii"
    lines = lines.split(";")
    return ("linia " if len(lines) == 1 else "linie ") + ", ".join(lines)


def card(n, r, stab, link, crop_name, crop_note):
    members = [m for m in r.place_members.split(";") if m != r.id]
    flags = [FLAG_PL[f] for f in r.flags.split(";")] if isinstance(r.flags, str) and r.flags else []
    trains = int(r.trains_per_day)
    vmax = "brak danych" if pd.isna(r.vmax_kmh) else f"{int(r.vmax_kmh)} km/h"
    lc = CROSSING_PL.get(r.legal_crossing_type, "legalne przejście")
    lines = [
        f"# {n}. {r.street} - {lines_text(r)} ({r.id})",
        "",
        f"**Wynik ryzyka: {num(r.score, 1)} / 100** (miejsce {n} z 20; punkt {r.id} ma pozycję {r.rank} z 82 kandydatów)",
        "",
        f"- Położenie: najbliższa ulica {r.street} ({dist(r.street_m)}), stacja {r.station} ({dist(r.station_m)}), "
        f"{lines_text(r)}. Współrzędne {r.lat:.5f}, {r.lon:.5f}.",
    ]
    if members:
        lines.append(f"- To samo miejsce (w promieniu 300 m): {', '.join(members)}.")
    lines += [
        f"- Geoportal (ortofotomapa): {link}",
        f"- Ortofoto 300 x 300 m (czerwone kółko = kandydat): ![{r.id}]({crop_name})" if crop_name else
        "- Ortofoto: nie udało się pobrać",
        "",
        "## Trzy czynniki",
        "",
        "| czynnik | wartość 0-1 | co to znaczy |",
        "|---|---|---|",
        f"| Ekspozycja (ilu ludzi ma powód przejść) | {num(r.E_exposure, 2)} | {num(r.pop_500m)} mieszkańców w 500 m "
        f"(strona A: {num(r.pop_500m_a)}, strona B: {num(r.pop_500m_b)}). Cele po stronie A: {dest_text(r.dest_list_a)}. "
        f"Cele po stronie B: {dest_text(r.dest_list_b)}. |",
        f"| Objazd (brak legalnej drogi) | {num(r.D_detour, 2)} | legalna droga {dist(r.detour_walk_m)} zamiast "
        f"{dist(r.detour_straight_m)} na skróty (objazd {dist(r.detour_m)}, {num(r.detour_ratio, 1)} razy dłużej); "
        f"najbliższe legalne przejście: {lc}. |",
        f"| Zagrożenie (pociągi, prędkość, tory) | {num(r.H_hazard, 2)} | {trains} pociągów pasażerskich na dobę "
        f"(środa 18.11.2026, wszystkie linie w 30 m), prędkość maks. {vmax}, torów do przejścia: {int(r.tracks_crossed)}. |",
        "",
    ]
    if flags:
        lines += ["## Uwagi", ""] + [f"- {f}" for f in flags] + [""]
    lines += [
        "## Zalecana interwencja",
        "",
        "- Etap 0 (od zaraz): patrol SOK 18-23 + pomiar ruchu przed/po."
        + ("" if r.intervention_primary == "I11_patrol_sok" else " Patrol zostaje do czasu wykonania rozwiązania głównego."),
        f"- Główna: **{r.primary_name}** - {r.primary_cost_text}.",
        f"- Wspierająca: {r.support_name} - {r.support_cost_text}." if isinstance(r.support_name, str) else
        "- Wspierająca: brak.",
        "- Zawsze dodatkowo: tablice z informacją o mandacie (600-4 000 zł) (reguła R0)."
        if "I9_tablice" not in (r.intervention_primary, r.intervention_support) else None,
        f"- Reguła doboru: {r.rule}. {rule_note(r)}",
    ]
    lines += [
        "",
        f"Stabilność: miejsce zostaje w top-20 w {num(100 * stab['one_at_a_time'])}% wariantów jednej zmiany "
        f"(+-50%) i w {num(100 * stab['monte_carlo'])}% z 2000 losowań wszystkich wag naraz.",
        "",
        f"Źródła: kandydat OSM ({r.sources}); ruch i prędkość PKP PLK (Regulamin sieci 2025/2026, zał. 2.1; rozkład "
        f"PolishTrainsGTFS); ludność GUS NSP 2021 (siatka 250 m); cele i sieć piesza OpenStreetMap; ortofoto Geoportal "
        f"(GUGiK). Ortofoto: {crop_note}.",
        "",
    ]
    return "\n".join(line for line in lines if line is not None)


def rule_note(r):
    if r.intervention_primary == "I5_przejscie_kat_E":
        return (f"Najtańsze rozwiązanie trwałe dopuszczalne prawnie: <= 3 tory i prędkość <= 160 km/h (§ 5, § 11). "
                f"Warunek: widoczność pociągu L2 = 3 x Vr = {int(r.sight_needed_m)} m z 4 m od skrajnej szyny "
                f"(Dz.U. 2025 poz. 1105, zał. 3 cz. C) - do sprawdzenia w terenie; bez widoczności potrzebny system "
                f"przejazdowy albo ograniczenie prędkości. Oświetlenie przejścia (8 000-15 500 zł/punkt) tylko jako "
                f"uzupełnienie - samo nie ma zmierzonego efektu.")
    if r.intervention_primary == "I6_kladka":
        return ("Ponad 3 tory lub prędkość > 160 km/h: przejście w poziomie szyn wymagałoby systemu przejazdowego "
                "(§ 11 ust. 2), więc najtańsze rozwiązanie bez niego to kładka lub tunel; alternatywa: kat. E z "
                "systemem przejazdowym (koszt nieustalony).")
    if r.intervention_primary == "I11_patrol_sok":
        return ("Niska ekspozycja: inwestycja nieuzasadniona, wystarczy patrol, tablice i pomiar ruchu.")
    if r.intervention_primary == "I13_przelozenie_dojscia_peron":
        return f"Kandydat {num(r.dist_platform_m)} m od peronu (próg: 150 m)."
    if r.intervention_primary == "I3_domkniecie_koncow_sciezki":
        return ("Objazd <= 300 m: ogrodzenie kanalizujące do istniejącego legalnego przejścia; warunek fińskiego "
                "badania, w którym ogrodzenie dało -94,6% przejść.")
    return ""


def main():
    rk = pd.read_csv(RANKING)
    stab = json.loads(SENSITIVITY.read_text())["top20_places_stability"]
    top = rk[rk["place_leader"] & (rk["place_rank"] <= TOP_N)].sort_values("place_rank")
    OUT.mkdir(parents=True, exist_ok=True)
    index = ["# Top-20 miejsc - dzikie przejścia przez tory, Wrocław", "",
             "| nr | id | miejsce | wynik | ekspozycja | objazd | zagrożenie | pociągi/dobę | vmax | interwencja | koszt |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(top.itertuples(), start=1):
        stem = f"{n:02d}_{r.id}"
        crop_path = OUT / f"{stem}.jpg"
        note = crop(r, crop_path)
        text = card(n, r, stab[r.id], r.geoportal_url, crop_path.name if note else None, note)
        (OUT / f"{stem}.md").write_text(text, encoding="utf-8")
        vmax = "-" if pd.isna(r.vmax_kmh) else int(r.vmax_kmh)
        index.append(f"| {n} | [{r.id}]({stem}.md) | {r.street}, {lines_text(r)} | {num(r.score, 1)} | {num(r.E_exposure, 2)} "
                     f"| {num(r.D_detour, 2)} ({dist(r.detour_m)}) | {num(r.H_hazard, 2)} | {int(r.trains_per_day)} | {vmax} "
                     f"| {r.primary_name} | {r.primary_cost_text} |")
        print(stem, note)
    (OUT / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
