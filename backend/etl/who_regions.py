"""WHO regional office membership by ISO3 (AFRO, AMRO, EMRO, EURO, SEARO, WPRO).

Used by the multi-region spread pattern. Static on purpose: a region lookup must not depend on a
network call. Territories not listed here simply have no region and are ignored by the pattern.
Review against https://www.who.int/about/who-we-are/regional-offices when publishing.
"""

_R = {
    "AFRO": "DZA AGO BEN BWA BFA BDI CMR CPV CAF TCD COM COG CIV COD GNQ ERI SWZ ETH GAB GMB GHA GIN GNB KEN "
            "LSO LBR MDG MWI MLI MRT MUS MOZ NAM NER NGA RWA STP SEN SYC SLE ZAF SSD TZA TGO UGA ZMB ZWE",
    "AMRO": "ATG ARG BHS BRB BLZ BOL BRA CAN CHL COL CRI CUB DMA DOM ECU SLV GRD GTM GUY HTI HND JAM MEX NIC PAN "
            "PRY PER KNA LCA VCT SUR TTO USA URY VEN PRI",
    "SEARO": "BGD BTN PRK IND IDN MDV MMR NPL LKA THA TLS",
    "EURO": "ALB AND ARM AUT AZE BLR BEL BIH BGR HRV CYP CZE DNK EST FIN FRA GEO DEU GRC HUN ISL IRL ISR ITA KAZ "
            "KGZ LVA LTU LUX MLT MCO MNE NLD MKD NOR POL PRT MDA ROU RUS SMR SRB SVK SVN ESP SWE CHE TJK TUR TKM "
            "UKR GBR UZB XKX",
    "EMRO": "AFG BHR DJI EGY IRN IRQ JOR KWT LBN LBY MAR OMN PAK PSE QAT SAU SOM SDN SYR TUN ARE YEM",
    "WPRO": "AUS BRN KHM CHN COK FJI JPN KIR LAO MYS MHL FSM MNG NRU NZL NIU PLW PNG PHL KOR WSM SGP SLB TON TUV "
            "VUT VNM TWN HKG MAC",
}

WHO_REGION: dict[str, str] = {iso: region for region, codes in _R.items() for iso in codes.split()}

assert len(WHO_REGION) == sum(len(c.split()) for c in _R.values()), "an ISO3 code appears in two regions"
