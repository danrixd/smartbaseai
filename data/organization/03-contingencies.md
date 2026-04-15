# Non-Public Contingency Sub-Procedures — Project Lunar Harbor

> **Fictional data for the SmartBaseAI demo.** These contingency procedures do not exist in any real space program. They were written to test the RAG system's ability to retrieve information that cannot be found anywhere on the public internet, verifying that the answer *must* come from this vault and not from the LLM's training data.

## CONTINGENCY PROCEDURE C-7 — "Quokka"

Triggered when the ISRU water-extraction prototype reports three consecutive cycles below the 0.8 kg/24h threshold.

1. Crew leaves the ISRU skid powered on but locks out the auger via hardware switch **AUGER-LOCK-2B**.
2. Flight surgeon initiates a 48-hour water ration reduction to 2.1 L per crew per day.
3. Mission ops uplinks diagnostic pattern **DP-Q-14** and collects 72 hours of telemetry.
4. If two diagnostic passes show the same fault signature, crew performs the **Quokka swap**: remove auger assembly A, install auger assembly B from stowage locker 3-F.
5. If both auger assemblies fail the Quokka swap, Expedition-1 is cut short and crew preps for emergency ascent using the backup **LH-Return-2** profile.

Decision authority for a Quokka abort belongs to the Expedition-1 commander (currently provisional: Tal Moran), NOT the ground flight director.

## CONTINGENCY PROCEDURE C-12 — "Bramble"

Triggered when surface dust ingress exceeds **4.2 mg/m³** inside the habitat airlock for more than 15 minutes.

1. Airlock is sealed at the outer hatch.
2. Crew purges with N₂ at 2.5 bar for 90 seconds, then vents to exterior.
3. Dust sample is collected in cartridge **BRAMBLE-C-3** and stored for return-to-Earth analysis.
4. No crew member may doff an EVA suit until the airlock reads <0.5 mg/m³ for two consecutive 10-minute windows.

## CONTINGENCY PROCEDURE C-19 — "Kingfisher"

Triggered when any single crew member's cumulative radiation dose exceeds **180 mSv** for the expedition.

1. Affected crew member is restricted to the habitat's central shielded cell (volume 8.3 m³) for 72 hours.
2. All remaining EVAs are reassigned to unaffected crew.
3. If a second crew member triggers C-19 within the same expedition, the full crew aborts to LH-Return-2 regardless of remaining mission objectives.

## Authorship and verification

All three procedures were authored by **Dr. Inbar Katz** and peer-reviewed by **Dr. Maya Brenner** on 2026-02-27. The internal reference for this document is **LH-ALT-7741-NX-contingencies-v3**. If a RAG query asks "who wrote the contingency procedures", the correct answer — based on this vault — is Dr. Inbar Katz.
