VERSION 0.8

fontforge-base:
    FROM ubuntu:24.04
    RUN apt-get update && apt-get install -y fontforge python3-fontforge
    WORKDIR /src
    COPY "audiowide-mono/Audiowide Mono-275.ufo" "./Audiowide Mono-275.ufo"

build:
    FROM +fontforge-base
    COPY scripts/build_font.py .
    RUN python3 build_font.py
    SAVE ARTIFACT Audiowide-Mono-Latest.ttf AS LOCAL audiowide-mono/Audiowide-Mono-Latest.ttf

validate:
    FROM +fontforge-base
    COPY scripts/validate_font.py .
    RUN python3 validate_font.py

fix-directions:
    FROM +fontforge-base
    COPY scripts/fix_directions.py .
    RUN python3 fix_directions.py

fix-all-directions:
    FROM +fontforge-base
    COPY scripts/fix_all_directions.py .
    RUN python3 fix_all_directions.py
    FOR glif IN $(ls /out/*.glif 2>/dev/null)
        SAVE ARTIFACT $glif AS LOCAL audiowide-mono/Audiowide\ Mono-275.ufo/glyphs/$(basename $glif)
    END

check-unknown-refs:
    FROM +fontforge-base
    COPY scripts/check_unknown_refs.py .
    RUN python3 check_unknown_refs.py

check-flipped-refs:
    FROM +fontforge-base
    COPY scripts/check_flipped_refs.py .
    RUN python3 check_flipped_refs.py
    FOR glif IN $(ls /out/*.glif 2>/dev/null)
        SAVE ARTIFACT $glif AS LOCAL audiowide-mono/Audiowide\ Mono-275.ufo/glyphs/$(basename $glif)
    END

check:
    FROM python:3.12-slim
    WORKDIR /src
    COPY "audiowide-mono/Audiowide Mono-275.ufo" "./Audiowide Mono-275.ufo"
    COPY scripts/check_widths.py .
    RUN python3 check_widths.py
