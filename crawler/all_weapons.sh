#!/usr/bin/zsh

for id in $(cat ../lib/weaponlist.json | jq -r ".data[].id"); do
  echo $id
  python weapon_ambr.py $id
done
