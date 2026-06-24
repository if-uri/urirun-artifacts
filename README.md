# urirun-artifacts

**Artifact data-model registry** — connector ekosystemu [ifURI / urirun](https://github.com/if-uri/urirun).
Schemat URI: `artifact://`

Rejestr modeli danych adresowany przez URI: *czym jest faktura, czym jest rachunek, czym jest paragon*. Każdy artifact to jeden model **Pydantic** (źródło prawdy), z którego **wyprowadzamy** JSON Schema, definicję **proto3/gRPC** oraz przykładową instancję — dzięki temu cztery reprezentacje, których potrzebuje pipeline biurowy, nigdy się nie rozjeżdżają. Dowolne query może przez `artifact://host/schema/query/get` dociągnąć oczekiwaną strukturę danego obiektu i załączyć ją jako kontekst.

A URI-addressable registry of artifact data models. One Pydantic model per artifact is the single source of truth; JSON Schema, proto3 and example instances are all derived from it, so any urirun query can attach an object's expected structure as context.

## Opis

- **Pydantic-first.** Definiujesz artifact jako model Pydantic + dekorator `@artifact("faktura", domain="accounting", ...)`. Reszta (JSON Schema, proto, przykład) jest generowana. Zaprojektowane pod setki typów.
- `artifact://host/registry/query/list` — wszystkie artifacts (`?domain=accounting` filtruje).
- `artifact://host/registry/query/domains` — mapa domena → id.
- `artifact://host/registry/query/search?q=vat` — szukanie po id/tytule/słowach kluczowych.
- `artifact://host/schema/query/get?name=faktura&fmt=json-schema|pydantic|proto` — **to jest trasa, którą query załącza oczekiwaną strukturę** (domyślnie JSON Schema Draft 2020-12).
- `artifact://host/schema/query/proto?name=faktura` — proto3 (jeden `message` na zagnieżdżony obiekt) do gRPC; opakowane usługą `grpc/artifacts.proto`.
- `artifact://host/schema/query/example?name=faktura` — minimalna przykładowa instancja.
- `artifact://host/schema/query/validate?name=faktura` (`data` = JSON) — walidacja payloadu względem modelu; bramka, zanim flow zaufa zeskanowanej fakturze.

Domeny startowe: **accounting** (`faktura`, `rachunek`, `paragon`), **documents** (`document`), **contacts** (`contact`). Nowy obiekt = jedna klasa + jeden dekorator w `urirun_artifacts/models/`.

### Przykład

```bash
# JSON Schema faktury — do załączenia w kontekście query
urirun run "artifact://host/schema/query/get?name=faktura&fmt=json-schema"

# walidacja payloadu sparsowanego przez invoice://
urirun-artifact validate --name faktura --data '{"number":"FV 7/2026","issueDate":"2026-05-13","seller":{"name":"ACME"},"buyer":{"name":"Klient"}}'

# proto3 do gRPC
urirun-artifact proto --name faktura
```

## Powiązania w pipeline

- `invoice://` wyciąga pola, które `Faktura` waliduje (`net/vat/gross/nip/...`).
- `camera://` skanuje paragon → `Paragon` → draft faktury.
- gRPC: `urirun_artifacts/grpc/artifacts.proto` to stabilna koperta usługi; komunikaty per-artifact generujesz z modeli (`fmt=proto`).

## Wymagania

- **python:** `urirun`, `pydantic>=2`
- **optional:** `grpcio-tools` (protoc), aby skompilować wygenerowane `.proto` do stubów gRPC

## Instalacja (dev)

```bash
pip install -e .
pytest -q
```

## Powiązane

- Rdzeń: [if-uri/urirun](https://github.com/if-uri/urirun)
- Widoki/HTML: [if-uri/urirun-widgets](https://github.com/if-uri/urirun-widgets)
- Hub connectorów: [connect.ifuri.com](https://connect.ifuri.com)

---
Kategoria: Data modelling · Słowa kluczowe: artifact, schema, pydantic, json-schema, protobuf, grpc, faktura, rachunek, paragon · Wydawca: if-uri
