#!/bin/sh
# Download the Microsoft Rocketbox (MIT) avatars and animations the presenter is built from.
# Only needed to rebuild the presenter; the rendered clips are already in assets/presenter.
set -e
cd "$(dirname "$0")"
B=https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets

fetch() {  # fetch <url> <dest>
    [ -s "$2" ] && return
    mkdir -p "$(dirname "$2")"
    echo "  $2"
    curl -sSfL --retry 3 -o "$2" "$1"
}

echo "Avatars (Male_Adult_11 body, Male_Adult_14 head):"
for a in Male_Adult_11:m001 Male_Adult_14:m012; do
    name=${a%%:*}; tex=${a##*:}
    fetch "$B/Avatars/Adults/$name/Export/$name.fbx" "$name/$name.fbx"
    for t in body_color body_normal body_specular head_color head_normal head_specular; do
        fetch "$B/Avatars/Adults/$name/Textures/${tex}_$t.tga" "$name/Textures/${tex}_$t.tga"
    done
done

echo "Animations:"
for a in all_animations_max_motextr_static/m_idle_neutral_01 \
         all_animations_max_motextr_static/m_gestic_talk_neutral_01 \
         all_animations_max_motextr_static/m_gestic_talk_neutral_02 \
         all_animations_max_motextr_static/m_gestic_talk_excited_01 \
         all_animations_max_motextr_static/m_gestic_presentation_right_01 \
         all_animations_max_motextr_static/m_wave_01 \
         all_animations_max_motextr_xy/m_walk_neutral_01 \
         all_animations_max_motextr_xyz/m_turn_left_90; do
    fetch "$B/Animations/$a.max.fbx" "anims/$(basename "$a").fbx"
done
echo "Done."
