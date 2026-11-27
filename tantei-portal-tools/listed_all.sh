#!/usr/bin/env bash
# listed-hero.yml の書き戻しで競合したときに、最新の main の上で掲載ページの組み直しをやり直す（2026-11-17）。
# 各スクリプトは何度実行しても同じ結果になる。撮影・背景画像は直前の結果（img/listed）を戻してから呼ぶので撮り直しはしない。
cd "$(dirname "$0")/.."
python tantei-portal-tools/render_listed.py || true
python tantei-portal-tools/google_rating.py render || true
python tantei-portal-tools/render_hp_types.py || true
python tantei-portal-tools/render_neighbors.py || true
python tantei-portal-tools/render_display_no.py || true
python tantei-portal-tools/render_kanri_no.py || true
python tantei-portal-tools/render_media_link.py || true
python tantei-portal-tools/render_llmo.py || true
python tantei-portal-tools/render_city_extra.py || true
python tantei-portal-tools/render_pref_extra.py || true
python tantei-portal-tools/render_counts.py || true
FORCE= python tantei-portal-tools/listed_heroes.py || true
FORCE= python tantei-portal-tools/listed_bg.py || true
python tantei-portal-tools/listed_geo.py || true
python tantei-portal-tools/render_recent.py || true
python tantei-portal-tools/render_listed_order.py || true
python tantei-portal-tools/render_gashi_banner.py || true
python tantei-portal-tools/make_sitemap.py || true
